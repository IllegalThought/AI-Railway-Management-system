import {
  Activity,
  CircleGauge,
  GitBranch,
  RadioTower,
  Siren,
  TrainFront,
  type LucideIcon,
} from "lucide-react";

export type NavigationItem = {
  href: string;
  label: string;
  description: string;
  icon: LucideIcon;
};

export const navigationItems: NavigationItem[] = [
  { href: "/", label: "Overview", description: "Network status and operational summary", icon: CircleGauge },
  { href: "/dispatch-board", label: "Dispatch Board", description: "Train and platform assignment workspace", icon: GitBranch },
  { href: "/live-operations", label: "Live Operations", description: "Current train movements and service state", icon: RadioTower },
  { href: "/network-monitor", label: "Network Monitor", description: "Infrastructure and route availability", icon: Activity },
  { href: "/incident-center", label: "Incident Center", description: "Operational disruptions and response", icon: Siren },
  { href: "/trains-platforms", label: "Trains & Platforms", description: "Fleet and platform records", icon: TrainFront },
];

export function getNavigationItem(pathname: string) {
  return navigationItems.find((item) => item.href === pathname) ?? navigationItems[0];
}
