import { useMemo, useState } from "react";

import { AdminActionButton } from "../../components/AdminActionButton";
import { MufasaAssistant } from "../../components/MufasaAssistant";
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
      { label: "View Audit Logs", endpoint: "/admin/memberships", method: "GET" },
    ],
  },
  {
    title: "Lead Intelligence",
    actions: [
      { label: "Ingest Leads", endpoint: "/leads/intelligence/ingest", method: "POST", payload: { source_name: "mufasa", source_type: "ai", leads: [{ property_address: "101 Elm St", city: "Dallas", state: "TX", foreclosure_stage: "pre_foreclosure" }] } },
      { label: "Ingest CSV Leads", endpoint: "/leads/intelligence/ingest-csv?source_name=csv_import&source_type=file", method: "POST" },
      { label: "Score Leads", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "score leads" } },
      { label: "Deduplicate Leads", endpoint: "/botops/leads/upsert", method: "POST", payload: [] },
      { label: "Create Case From Lead", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "create case from lead" } },
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
      { label: "Create Veteran Profile", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "discover veteran benefits" } },
      { label: "Scan Veteran Benefits", endpoint: "/partners/veterans/benefit-discovery-summary", method: "GET" },
      { label: "Generate Veteran Action Plan", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "generate veteran action plan" } },
      { label: "Generate Veteran Documents", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "generate veteran documents" } },
    ],
  },
  {
    title: "Partner Routing",
    actions: [
      { label: "Route Case to Partner", endpoint: "/partners/route-case", method: "POST", payload: {} },
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
      { label: "Start Training Lesson", endpoint: "/training/step/1", method: "GET" },
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
        payload: { prompt: "show capabilities" },
      },
      {
        label: "Send AI Prompt",
        endpoint: "/admin/ai/mufasa/chat",
        method: "POST",
        payload: { prompt: "run diagnostics and summarize status" },
      },
      { label: "Run AI Automation", endpoint: "/admin/ai/mufasa/chat", method: "POST", payload: { prompt: "verify platform and run diagnostics" } },
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
        <MufasaAssistant />

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16, marginTop: 16 }}>
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
