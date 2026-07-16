export function getReleaseMetadata() {
  const architectureVersion = import.meta.env.VITE_ARCH_VERSION || "0.1.x";
  const buildId = import.meta.env.VITE_BUILD_NUMBER || "0000";
  const backendTestCount = Number(import.meta.env.VITE_BACKEND_TEST_COUNT || "289");

  return {
    bridgeName: "Bridge Zero",
    epoch: "Epoch VIII",
    architectureVersion,
    buildId,
    backendTestCount,
  };
}
