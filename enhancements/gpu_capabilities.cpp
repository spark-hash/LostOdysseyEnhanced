// Isolated capability query: no game, swapchain, frame generation or model evaluation.
#define NOMINMAX
#include <windows.h>
#include <dxgi1_4.h>
#include <d3d12.h>
#include <wrl/client.h>
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include <nvsdk_ngx.h>
#include <nvsdk_ngx_vk.h>
#include <sl_core_api.h>
#include <sl_dlss_g.h>
#include <sl_security.h>
#include <json.hpp>
#include <filesystem>
#include <fstream>
#include <vector>
#include <cstring>

using Microsoft::WRL::ComPtr;
using nlohmann::json;
constexpr auto projectId = "bb5fe48b-f929-4b9a-a72b-98a23141a7c9";
template<class T> T symbol(HMODULE dll, const char* name) { return reinterpret_cast<T>(GetProcAddress(dll,name)); }
std::string utf8(const wchar_t* text) {
    int length=WideCharToMultiByte(CP_UTF8,0,text,-1,nullptr,0,nullptr,nullptr);
    std::string result(length,'\0');
    WideCharToMultiByte(CP_UTF8,0,text,-1,result.data(),length,nullptr,nullptr);
    result.pop_back(); return result;
}
struct Discovery {
    std::wstring root, cache;
    const wchar_t* paths[1];
    NVSDK_NGX_FeatureCommonInfo common{};
    NVSDK_NGX_FeatureDiscoveryInfo info{};
    Discovery(const std::filesystem::path& runtime,const std::filesystem::path& data)
        : root(runtime.wstring()),cache(data.wstring()),paths{root.c_str()} {
        common.PathListInfo.Path=paths; common.PathListInfo.Length=1;
        info.SDKVersion=NVSDK_NGX_Version_API; info.FeatureID=NVSDK_NGX_Feature_SuperSampling;
        info.Identifier.IdentifierType=NVSDK_NGX_Application_Identifier_Type_Project_Id;
        info.Identifier.v.ProjectDesc={projectId,NVSDK_NGX_ENGINE_TYPE_CUSTOM,"LostOdysseyRecomp"};
        info.ApplicationDataPath=cache.c_str(); info.FeatureInfo=&common;
    }
};
struct Streamline {
    HMODULE dll{}; bool initialized=false;
    PFun_slShutdown* shutdown{};
    PFun_slIsFeatureSupported* supported{};
    PFun_slGetFeatureFunction* function{};
    ~Streamline() { if(initialized && shutdown) shutdown(); if(dll) FreeLibrary(dll); }
    bool init(const std::filesystem::path& root,const std::filesystem::path& cache,bool vulkan,json& report) {
        for(auto name:{L"sl.interposer.dll",L"sl.common.dll",L"sl.dlss_g.dll",L"sl.reflex.dll",L"sl.pcl.dll"}) {
            if(!sl::security::verifyEmbeddedSignature((root/name).c_str())) {
                report["fg_reason"]="Missing or invalid Streamline signature"; return false;
            }
        }
        dll=LoadLibraryExW((root/L"sl.interposer.dll").c_str(),nullptr,
            LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
        if(!dll) { report["fg_reason"]="Streamline load failed"; return false; }
        auto initialize=symbol<PFun_slInit*>(dll,"slInit");
        shutdown=symbol<PFun_slShutdown*>(dll,"slShutdown");
        supported=symbol<PFun_slIsFeatureSupported*>(dll,"slIsFeatureSupported");
        function=symbol<PFun_slGetFeatureFunction*>(dll,"slGetFeatureFunction");
        if(!initialize||!shutdown||!supported||!function) return false;
        const wchar_t* paths[]={root.c_str()};
        const sl::Feature features[]={sl::kFeatureDLSS_G,sl::kFeatureReflex,sl::kFeaturePCL};
        sl::Preferences p{}; p.pathsToPlugins=paths;p.numPathsToPlugins=1;
        p.pathToLogsAndData=nullptr;p.featuresToLoad=features;p.numFeaturesToLoad=3;
        p.renderAPI=vulkan?sl::RenderAPI::eVulkan:sl::RenderAPI::eD3D12;
        p.flags=sl::PreferenceFlags::eUseManualHooking|sl::PreferenceFlags::eDisableCLStateTracking|
            sl::PreferenceFlags::eUseFrameBasedResourceTagging;
        p.projectId=projectId;p.engine=sl::EngineType::eCustom;p.engineVersion="LostOdysseyRecomp";
        auto result=initialize(p,sl::kSDKVersion);report["sl_init_result"]=int(result);
        initialized=result==sl::Result::eOk;return initialized;
    }
};
json probeD3D(IDXGIAdapter1* adapter,const std::filesystem::path& root,const std::filesystem::path& cache) {
    json report={{"sr",false},{"fg",false},{"max_multiplier",1},{"dynamic",false}};
    ComPtr<ID3D12Device> device;
    if(FAILED(D3D12CreateDevice(adapter,D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device)))) return report;
    Discovery discovery(root,cache);
    auto result=NVSDK_NGX_D3D12_Init_with_ProjectID(projectId,NVSDK_NGX_ENGINE_TYPE_CUSTOM,
        "LostOdysseyRecomp",discovery.cache.c_str(),device.Get(),&discovery.common);
    report["ngx_init_result"]=uint32_t(result);
    if(NVSDK_NGX_SUCCEED(result)) {
        NVSDK_NGX_Parameter* params=nullptr;
        if(NVSDK_NGX_SUCCEED(NVSDK_NGX_D3D12_GetCapabilityParameters(&params))&&params) {
            int available=0,update=0;
            auto status=NVSDK_NGX_Parameter_GetI(params,NVSDK_NGX_EParameter_SuperSampling_Available,&available);
            NVSDK_NGX_Parameter_GetI(params,NVSDK_NGX_Parameter_SuperSampling_NeedsUpdatedDriver,&update);
            report["sr"]=NVSDK_NGX_SUCCEED(status)&&available!=0&&update==0;
            NVSDK_NGX_D3D12_DestroyParameters(params);
        }
        NVSDK_NGX_D3D12_Shutdown1(device.Get());
    }
    Streamline sl;
    if(!sl.init(root,cache,false,report)) return report;
    auto setDevice=symbol<PFun_slSetD3DDevice*>(sl.dll,"slSetD3DDevice");
    if(!setDevice||setDevice(device.Get())!=sl::Result::eOk) return report;
    auto luid=device->GetAdapterLuid();sl::AdapterInfo info{};
    info.deviceLUID=reinterpret_cast<uint8_t*>(&luid);info.deviceLUIDSizeInBytes=sizeof(luid);
    auto support=sl.supported(sl::kFeatureDLSS_G,info);report["fg_support_result"]=int(support);
    if(support!=sl::Result::eOk) return report;
    void* raw=nullptr;
    if(sl.function(sl::kFeatureDLSS_G,"slDLSSGGetState",raw)!=sl::Result::eOk||!raw) return report;
    sl::DLSSGState state{};
    auto queried=reinterpret_cast<PFun_slDLSSGGetState*>(raw)(sl::ViewportHandle(0),state,nullptr);
    report["fg_state_result"]=int(queried);
    if(queried==sl::Result::eOk&&state.numFramesToGenerateMax>0) {
        report["fg"]=true;report["max_multiplier"]=std::min(6u,state.numFramesToGenerateMax+1);
        report["dynamic"]=state.bIsDynamicMFGSupported==sl::eTrue;
    }
    return report;
}
json probeVulkan(const DXGI_ADAPTER_DESC1& desc,const std::filesystem::path& root,const std::filesystem::path& cache) {
    json report={{"sr",false},{"fg",false},{"dynamic",false}};
    HMODULE loader=LoadLibraryExW(L"vulkan-1.dll",nullptr,LOAD_LIBRARY_SEARCH_SYSTEM32);
    if(!loader) return report;
    auto gipa=symbol<PFN_vkGetInstanceProcAddr>(loader,"vkGetInstanceProcAddr");
    auto create=gipa?reinterpret_cast<PFN_vkCreateInstance>(gipa(nullptr,"vkCreateInstance")):nullptr;
    VkApplicationInfo application{VK_STRUCTURE_TYPE_APPLICATION_INFO};application.apiVersion=VK_API_VERSION_1_1;
    VkInstanceCreateInfo setup{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};setup.pApplicationInfo=&application;
    VkInstance instance{};
    if(!create||create(&setup,nullptr,&instance)!=VK_SUCCESS) { FreeLibrary(loader);return report; }
    auto enumerate=reinterpret_cast<PFN_vkEnumeratePhysicalDevices>(gipa(instance,"vkEnumeratePhysicalDevices"));
    auto properties=reinterpret_cast<PFN_vkGetPhysicalDeviceProperties2>(gipa(instance,"vkGetPhysicalDeviceProperties2"));
    auto destroy=reinterpret_cast<PFN_vkDestroyInstance>(gipa(instance,"vkDestroyInstance"));
    uint32_t count=0;enumerate(instance,&count,nullptr);
    std::vector<VkPhysicalDevice> devices(count);enumerate(instance,&count,devices.data());
    for(auto physical:devices) {
        VkPhysicalDeviceIDProperties id{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_ID_PROPERTIES};
        VkPhysicalDeviceProperties2 props{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};props.pNext=&id;
        properties(physical,&props);
        if(!id.deviceLUIDValid||std::memcmp(id.deviceLUID,&desc.AdapterLuid,sizeof(LUID))) continue;
        report["device_name"]=props.properties.deviceName;
        Discovery discovery(root,cache);NVSDK_NGX_FeatureRequirement requirement{};
        auto queried=NVSDK_NGX_VULKAN_GetFeatureRequirements(instance,physical,&discovery.info,&requirement);
        report["ngx_requirements_result"]=uint32_t(queried);
        report["sr"]=NVSDK_NGX_SUCCEED(queried)&&requirement.FeatureSupported==NVSDK_NGX_FeatureSupportResult_Supported;
        {
            Streamline sl;
            if(sl.init(root,cache,true,report)) {
                sl::AdapterInfo info{};info.vkPhysicalDevice=physical;
                auto supported=sl.supported(sl::kFeatureDLSS_G,info);
                report["fg_support_result"]=int(supported);report["fg"]=supported==sl::Result::eOk;
            }
        }
        break;
    }
    destroy(instance,nullptr);FreeLibrary(loader);return report;
}
int wmain(int argc,wchar_t** argv) {
    if(argc<3) return 2;
    json output;
    try {
        wchar_t executable[MAX_PATH];GetModuleFileNameW(nullptr,executable,MAX_PATH);
        auto root=std::filesystem::path(executable).parent_path();
        auto cache=std::filesystem::path(argv[1]).parent_path()/L"sdk-cache";
        std::filesystem::create_directories(cache);
        ComPtr<IDXGIFactory4> factory;
        if(FAILED(CreateDXGIFactory1(IID_PPV_ARGS(&factory)))) throw std::runtime_error("DXGI unavailable");
        if(std::wstring(argv[2])==L"list") {
            output["adapters"]=json::array();
            for(UINT index=0;;++index) {
                ComPtr<IDXGIAdapter1> adapter;if(factory->EnumAdapters1(index,&adapter)==DXGI_ERROR_NOT_FOUND) break;
                DXGI_ADAPTER_DESC1 desc{};adapter->GetDesc1(&desc);
                if(desc.Flags&(DXGI_ADAPTER_FLAG_SOFTWARE|DXGI_ADAPTER_FLAG_REMOTE)) continue;
                output["adapters"].push_back({{"index",index},{"name",utf8(desc.Description)},
                    {"vendor",desc.VendorId},{"memory",uint64_t(desc.DedicatedVideoMemory)}});
            }
        } else {
            UINT index=std::stoul(argv[2]);ComPtr<IDXGIAdapter1> adapter;
            if(FAILED(factory->EnumAdapters1(index,&adapter))) throw std::runtime_error("Adapter unavailable");
            DXGI_ADAPTER_DESC1 desc{};adapter->GetDesc1(&desc);
            output=(argc>3&&std::wstring(argv[3])==L"vulkan")?probeVulkan(desc,root,cache):probeD3D(adapter.Get(),root,cache);
            output["name"]=utf8(desc.Description);output["index"]=index;
        }
    } catch(const std::exception& error) { output={{"error",error.what()}}; }
    std::ofstream(std::filesystem::path(argv[1]))<<output.dump(2);
    return output.contains("error")?1:0;
}
