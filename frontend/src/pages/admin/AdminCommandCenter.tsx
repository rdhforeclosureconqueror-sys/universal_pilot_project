import { useMemo, useState } from "react";

import { AdminActionButton } from "../../components/AdminActionButton";
import { HttpMethod } from "../../services/apiClient";

type ActionConfig = {
  label: string;
  endpoint: string;
  method: HttpMethod;
  payload?: unknown;
};

type SectionConfig = {
  title: string;
  actions: ActionConfig[];
};

const capabilitySections: SectionConfig[] = [
  {
    title: "System Operations",
    actions: [
      { label: "Verify System Health", endpoint: "/admin/system/verify/phase10", method: "POST" },
      { label: "Run AI Diagnostics", endpoint: "/verify/policy-engine", method: "GET" },
      { label: "View Capability Report", endpoint: "/platform/capabilities", method: "GET" },
      { label: "View Audit Logs", endpoint: "/admin/dashboard/ai-command-logs", method: "GET" },
    ],
  },
  {
    title: "Lead Intelligence",
    actions: [
      { label: "Ingest Leads", endpoint: "/lead-intelligence/ingest", method: "POST", payload: { leads: [] } },
      { label: "Ingest CSV Leads", endpoint: "/lead-intelligence/ingest-csv", method: "POST", payload: { csv_data: "" } },
      { label: "Score Leads", endpoint: "/lead-intelligence/score", method: "POST", payload: { leads: [] } },
      { label: "Deduplicate Leads", endpoint: "/botops/leads/upsert", method: "POST", payload: [] },
      { label: "Create Case From Lead", endpoint: "/pipeline/foreclosure-analysis", method: "POST", payload: { lead_id: "" } },
    ],
  },
  {
    title: "Foreclosure Intelligence",
    actions: [
      { label: "Create Foreclosure Profile", endpoint: "/foreclosure/create-profile", method: "POST", payload: {} },
      { label: "Update Foreclosure Status", endpoint: "/cases", method: "POST", payload: { status: "new" } },
      { label: "Calculate Case Priority", endpoint: "/foreclosure/analyze-property", method: "POST", payload: {} },
      { label: "Run Foreclosure Scan", endpoint: "/verify/phase9", method: "GET" },
    ],
  },
  {
    title: "Skiptrace",
    actions: [
      { label: "Skiptrace Property Owner", endpoint: "/verify/skiptrace-integration", method: "GET" },
      { label: "Skiptrace Case Owner", endpoint: "/verify/skiptrace-integration", method: "GET" },
      { label: "Batch Skiptrace", endpoint: "/verify/dfw-connectors", method: "GET" },
    ],
  },
  {
    title: "Essential Worker Housing",
    actions: [
      { label: "Create Worker Profile", endpoint: "/essential-worker/profile", method: "POST", payload: {} },
      { label: "Discover Housing Programs", endpoint: "/essential-worker/discover-benefits", method: "POST", payload: {} },
      { label: "Calculate Assistance Value", endpoint: "/impact/housing-summary", method: "GET" },
      { label: "Generate Homebuyer Action Plan", endpoint: "/essential-worker/action-plan", method: "POST", payload: {} },
    ],
  },
  {
    title: "Veteran Intelligence",
    actions: [
      { label: "Create Veteran Profile", endpoint: "/veteran-intelligence/profile", method: "POST", payload: {} },
      { label: "Scan Veteran Benefits", endpoint: "/partners/veterans/benefit-discovery-summary", method: "GET" },
      { label: "Generate Veteran Action Plan", endpoint: "/admin/ai/run-autopilot", method: "POST", payload: { domain: "veteran" } },
      { label: "Generate Veteran Documents", endpoint: "/admin/ai/summarize-case", method: "POST", payload: { context: "veteran-documents" } },
    ],
  },
  {
    title: "Partner Routing",
    actions: [
      { label: "Route Case to Partner", endpoint: "/partners/housing/route-case", method: "POST", payload: {} },
      { label: "View Partner Reports", endpoint: "/impact/opportunity-map", method: "GET" },
    ],
  },
  {
    title: "Portfolio",
    actions: [
      { label: "Add Property to Portfolio", endpoint: "/portfolio/add-property", method: "POST", payload: {} },
      { label: "View Portfolio Summary", endpoint: "/portfolio/summary", method: "GET" },
    ],
  },
  {
    title: "Training",
    actions: [
      { label: "Start Training Lesson", endpoint: "/training/step/intake", method: "GET" },
      { label: "Complete Training Lesson", endpoint: "/training/quiz_attempt", method: "POST", payload: {} },
      { label: "View Certifications", endpoint: "/training/system-overview", method: "GET" },
    ],
  },
  {
    title: "AI Command Center",
    actions: [
      {
        label: "Open Mufasa Assistant",
        endpoint: "/admin/ai/mufasa/chat",
        method: "POST",
        payload: { message: "show capabilities" },
      },
      {
        label: "Send AI Prompt",
        endpoint: "/admin/ai/mufasa/chat",
        method: "POST",
        payload: { message: "run diagnostics and summarize status" },
      },
      { label: "Run AI Automation", endpoint: "/admin/ai/run-autopilot", method: "POST", payload: { dry_run: true } },
      { label: "Generate Investor Report", endpoint: "/impact/summary", method: "GET" },
    ],
  },
];

const AdminCommandCenter = () => {
  const [history, setHistory] = useState<unknown[]>([]);

  const panelOutput = useMemo(() => {
    if (!history.length) {
      return "Run an admin action to view API responses in the console.";
    }
    return JSON.stringify(history, null, 2);
  }, [history]);

  return (
    <div className="admin-command-center" style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
      <div>
        <h1>Admin Command Center</h1>
        <p>Execute platform capabilities by section. All actions call backend APIs directly.</p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
          {capabilitySections.map((section) => (
            <article
              key={section.title}
              style={{ border: "1px solid #d7deeb", borderRadius: 10, padding: 14, background: "#ffffff" }}
            >
              <h3>{section.title}</h3>
              <div style={{ display: "grid", gap: 8 }}>
                {section.actions.map((action) => (
                  <AdminActionButton
                    key={`${section.title}-${action.label}`}
                    label={action.label}
                    endpoint={action.endpoint}
                    method={action.method}
                    payload={action.payload}
                    onResult={(result) => setHistory((previous) => [result, ...previous].slice(0, 50))}
                  />
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>

      <aside style={{ border: "1px solid #d7deeb", borderRadius: 10, background: "#0d1324", color: "#e9efff", padding: 14 }}>
        <h3 style={{ marginTop: 0 }}>Response Console</h3>
        <p style={{ color: "#8fa3d9" }}>Latest API responses and errors are logged here.</p>
        <pre style={{ whiteSpace: "pre-wrap", overflow: "auto", maxHeight: "75vh" }}>{panelOutput}</pre>
      </aside>
    </div>
  );
};

export default AdminCommandCenter;