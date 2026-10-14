#include "../upstream/LostOdysseyRecomp/gpu/aspect_ratio.h"
#include "../upstream/LostOdysseyRecomp/gpu/render_resolution.h"
#include <cassert>
#define LO_GPU_PLUME 1
#include "../upstream/LostOdysseyRecomp/gpu/dlss_sr.h"
static_assert(gpu::dlss::kMaxNeuralRenderingPasses == 5);
int main() {
    using namespace gpu::aspect_ratio;
    assert(Fit(Mode::SuperUltrawide, 5120, 1440) == (Extent{5120,1440}));
    assert(Fit(Mode::SuperUltrawide, 1920, 1080) == (Extent{1920,540}));
    assert(Fit(Mode::WideTall, 1920, 1080) == (Extent{1728,1080}));
    assert(Fit(Mode::WideTall, 2560, 1600) == (Extent{2560,1600}));
    assert(Fit(Mode::Ultrawide, 3440, 1440) == (Extent{3440,1440}));
}
