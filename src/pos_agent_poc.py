from __future__ import annotations

from datetime import datetime
from pathlib import Path

from poc_support import (
    AssetRepository,
    ITSMRepository,
    MockPlatformTools,
    SOPRetriever,
    Ticket,
    choose_primary_pos_asset,
    infer_family,
    load_config,
    render_history,
)


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "poc_config.json"
OUTPUT_DIR = ROOT / "outputs"


def build_ticket(config: dict) -> Ticket:
    demo_ticket = config["demo_ticket"]
    return Ticket(
        ticket_id=demo_ticket["ticket_id"],
        store_code=demo_ticket["store_code"],
        location_label=demo_ticket["location_label"],
        issue=demo_ticket["issue"],
        priority=demo_ticket["priority"],
        description=demo_ticket["description"],
    )


def run_demo() -> tuple[str, str]:
    config = load_config(CONFIG_PATH)
    ticket = build_ticket(config)

    asset_repo = AssetRepository((ROOT / config["asset_csv"]).resolve())
    itsm_repo = ITSMRepository((ROOT / config["itsm_xlsx"]).resolve())
    retriever = SOPRetriever((ROOT / config["sop_docx"]).resolve())
    tools = MockPlatformTools(config["heartbeat_defaults"])

    asset_store_id = config["store_alias_map"].get(ticket.store_code)
    store_assets = asset_repo.get_assets_for_store(asset_store_id) if asset_store_id else []
    pos_assets = asset_repo.get_pos_assets_for_store(asset_store_id) if asset_store_id else []
    primary_pos = choose_primary_pos_asset(pos_assets)

    issue_history = itsm_repo.history_for_store(ticket.store_code)
    history_summary = itsm_repo.recurring_issue_summary(ticket.store_code)

    model_name = primary_pos["Model"] if primary_pos else "Unknown POS model"
    model_family = infer_family(model_name, config["model_family_map"])
    retrieval_query = f"{ticket.issue} {model_name} restart sequence connectivity frozen terminal"
    sop_hits = retriever.retrieve(retrieval_query)

    heartbeat_status = tools.check_pos_heartbeat(ticket.store_code)
    asset_handle = f"{asset_store_id}:{model_name}" if asset_store_id else ticket.store_code
    port_reset_result = tools.trigger_port_reset(asset_handle) if heartbeat_status == "Offline" else "Port reset skipped."

    comment = (
        f"Agent triage complete for {ticket.location_label}. "
        f"Primary POS model: {model_name}. Heartbeat: {heartbeat_status}. "
        f"Recommended action: remote port reset and guided restart sequence."
    )
    comment_result = tools.update_incident_comment(ticket.ticket_id, comment)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_lines = [
        "POS Incident Agent POC Execution Log",
        f"Run Timestamp: {timestamp}",
        f"Retrieval Mode: {retriever.mode}",
        "",
        f"Input Ticket: {ticket.ticket_id}",
        f"Ticket Description: {ticket.description}",
        f"Priority: {ticket.priority}",
        "",
        "Agent Thought:",
        (
            f"I identified this as a high-frequency POS issue for {ticket.location_label}. "
            f"{history_summary}"
        ),
        (
            f"I reconciled the ITSM location code to CMDB store ID {asset_store_id} "
            "using the local alias map for this POC."
        ),
        (
            f"I selected {model_name} as the primary POS asset and inferred the provider family as "
            f"{model_family}."
        ),
        "I am retrieving the restart runbook from the Knowledge Lake and validating live heartbeat status.",
        "",
        "Enrichment:",
        f"CMDB Store ID: {asset_store_id}",
        f"POS Assets Found: {len(pos_assets)}",
        f"Primary POS Model: {model_name}",
        f"Primary POS Status: {primary_pos['Status'] if primary_pos else 'Unknown'}",
        "",
        "Historical Evidence:",
    ]

    log_lines.extend(render_history(issue_history))
    log_lines.extend(
        [
            "",
            "Retrieved SOP Context:",
        ]
    )
    for hit in sop_hits:
        log_lines.append(f"- [distance={hit.score}] {hit.chunk}")

    log_lines.extend(
        [
            "",
            "Action Taken:",
            f"check_pos_heartbeat({ticket.store_code}) -> {heartbeat_status}",
            f"trigger_port_reset({asset_handle}) -> {port_reset_result}",
            f"update_incident_comment({ticket.ticket_id}, ...) -> {comment_result}",
            "",
            "Output Summary:",
            (
                f"The POS at {ticket.location_label} is currently {heartbeat_status.lower()}. "
                f"The mapped CMDB record points to {model_name} ({model_family}). "
                "The recommended next-best action is to follow the SOP restart sequence: "
                "attempt a soft shutdown, perform a 5-10 second power cycle if frozen, wait 30 seconds, "
                "and refresh attached peripherals before retrying service."
            ),
            (
                f"{port_reset_result} Historical incidents suggest repeated terminal freezes at this "
                "location, so the store manager should monitor for recurrence after restart and escalate "
                "after two failed restart attempts."
            ),
        ]
    )

    summary_lines = [
        f"Ticket {ticket.ticket_id} for {ticket.location_label} was triaged as a likely recurring POS outage.",
        f"Asset enrichment mapped the store to {asset_store_id} and selected {model_name} as the primary POS device.",
        f"Heartbeat returned {heartbeat_status}, so the agent simulated a remote port reset and posted an incident update.",
        "Recommended store-manager resolution: follow the SOP restart sequence, verify peripherals, and escalate after two failed restart attempts.",
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_text = "\n".join(log_lines)
    summary_text = "\n".join(summary_lines)
    (OUTPUT_DIR / "pos_incident_demo_log.txt").write_text(log_text, encoding="utf-8")
    (OUTPUT_DIR / "pos_incident_summary.txt").write_text(summary_text, encoding="utf-8")
    return log_text, summary_text


if __name__ == "__main__":
    log_text, summary_text = run_demo()
    print(log_text)
    print("\n" + "=" * 72 + "\n")
    print(summary_text)
