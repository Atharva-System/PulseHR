import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { AuthGateSkeleton } from "@/components/shared/Skeleton";

interface Props {
  allowedRoles: string[];
}

export default function ProtectedRoute({ allowedRoles }: Props) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <AuthGateSkeleton />;
  }

  if (!user) return <Navigate to="/login" replace />;
  if (!allowedRoles.includes(user.role))
    return <Navigate to="/login" replace />;

  return <Outlet />;
}
