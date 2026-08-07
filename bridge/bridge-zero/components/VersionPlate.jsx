import DataPlate from "../instruments/DataPlate";

export default function VersionPlate({ metadata }) {
  const lines = [
    "Bridge Zero",
    metadata.epoch,
    `Architecture v${metadata.architectureVersion}`,
    `Build ${metadata.buildId}`,
    `${metadata.backendTestCount} Backend Tests`,
  ];

  return <DataPlate title="Version Plate" lines={lines} />;
}
