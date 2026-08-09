export function getReleaseMetadata() {
  const architectureVersion = import.meta.env.VITE_ARCH_VERSION || "0.5.0";
  const buildId = import.meta.env.VITE_BUILD_NUMBER || "0000";
  const backendTestCount = Number(import.meta.env.VITE_BACKEND_TEST_COUNT || "397");

  return {
    bridgeName: "Bridge Zero",
    epoch: "Epoch XII",
    architectureVersion,
    buildId,
    backendTestCount,
  };
}
