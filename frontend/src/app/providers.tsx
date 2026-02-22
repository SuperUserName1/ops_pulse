import { useEffect, type PropsWithChildren } from "react";

import { useAuthStore } from "@/features/auth/model/auth-store";

function AuthBootstrap({ children }: PropsWithChildren) {
  const bootstrap = useAuthStore((state) => state.bootstrap);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  return children;
}

export function AppProviders({ children }: PropsWithChildren) {
  return <AuthBootstrap>{children}</AuthBootstrap>;
}
