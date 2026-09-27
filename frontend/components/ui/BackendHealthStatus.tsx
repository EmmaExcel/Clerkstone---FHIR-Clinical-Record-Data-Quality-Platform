"use client";

import { useQuery } from "@tanstack/react-query";
import { NotificationBanner } from "nhsuk-react-components";
import { getApiBaseUrl, getHealth, isBackendOffline } from "@/lib/api";
import { BackendOffline } from "./BackendOffline";
import { LoadingState } from "./AsyncStatus";

export function BackendHealthStatus() {
  const query = useQuery({ queryKey: ["health"], queryFn: getHealth });

  if (query.isPending) {
    return <LoadingState label="Checking backend status" />;
  }

  if (query.isError) {
    if (isBackendOffline(query.error)) {
      return <BackendOffline retry={() => query.refetch()} />;
    }
    return (
      <NotificationBanner disableAutoFocus>
        <NotificationBanner.Title>Backend error</NotificationBanner.Title>
        The API responded with an error. See the console for details.
      </NotificationBanner>
    );
  }

  return null;
}
