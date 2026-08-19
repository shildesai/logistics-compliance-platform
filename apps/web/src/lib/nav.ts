export interface NavItem {
  label: string;
  href: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Assurance Overview", href: "/overview" },
  { label: "Controls", href: "/controls" },
  { label: "Evidence", href: "/evidence" },
  { label: "Findings", href: "/findings" },
  { label: "Corrective Actions", href: "/corrective-actions" },
  { label: "Audit Readiness", href: "/audit-readiness" },
  { label: "Compliance Assistant", href: "/compliance-assistant" },
  { label: "Administration", href: "/administration" },
];
