from utils.logger import logger
from agents.eda_preprocessing import AgentEventEmitter
from typing import Dict, List, Any, Optional
from datetime import datetime

# Helper function to generate proposals based on multiple inputs
def generate_proposal(
    identifier: str,
    causes: List[Dict[str, Any]],
    predictions: Dict[str, List[float]],
    kpis: Dict[str, Dict[str, float]],
    thresholds: Dict[str, float]
) -> List[Dict[str, Any]]:
    """Generate optimization proposals based on root causes, predictions, and KPIs."""
    proposals = []

    # Handle empty or missing inputs gracefully
    if not causes and not predictions and not kpis:
        return [{"description": "Manual investigation required", "confidence": 0.5, "details": {}}]

    # Analyze root causes
    for cause in causes:
        cause_desc = cause.get("description", "").lower()
        confidence = cause.get("confidence", 0.5)
        details = cause.get("details", {})
        
        if "interference" in cause_desc:
            proposals.append({
                "description": "Adjust antenna tilt by 2 degrees or increase power by 3 dBm",
                "confidence": min(0.9, confidence + 0.2),
                "details": {"action": "interference_mitigation", **details}
            })
        elif "congestion" in cause_desc:
            proposals.append({
                "description": "Reallocate spectrum or offload traffic to adjacent cells",
                "confidence": min(0.9, confidence + 0.2),
                "details": {"action": "congestion_relief", **details}
            })
        else:
            proposals.append({
                "description": "Manual investigation required due to unidentified cause",
                "confidence": confidence,
                "details": {"cause": cause_desc, **details}
            })

    # Analyze predictions
    for col, pred_values in predictions.items():
        if len(pred_values) > 0:
            trend = (pred_values[-1] - pred_values[0]) / len(pred_values)
            if col.lower() == "throughput" and trend < -thresholds["throughput_decline"]:
                proposals.append({
                    "description": "Increase capacity by adding carriers or upgrading hardware",
                    "confidence": 0.85,
                    "details": {"predicted_throughput_trend": trend, "future_values": pred_values}
                })
            elif col.lower() == "latency" and trend > thresholds["latency_increase"]:
                proposals.append({
                    "description": "Optimize QoS settings or reduce network load",
                    "confidence": 0.85,
                    "details": {"predicted_latency_trend": trend, "future_values": pred_values}
                })

    # Analyze KPIs
    for col, kpi in kpis.items():
        if col.lower() == "throughput" and kpi["mean"] < thresholds["throughput_low"]:
            proposals.append({
                "description": "Enhance throughput by optimizing resource allocation",
                "confidence": 0.8,
                "details": {"current_throughput": kpi["mean"], "std": kpi["std"]}
            })
        elif col.lower() == "latency" and kpi["mean"] > thresholds["latency_high"]:
            proposals.append({
                "description": "Reduce latency by prioritizing critical traffic",
                "confidence": 0.8,
                "details": {"current_latency": kpi["mean"], "std": kpi["std"]}
            })

    # Deduplicate and rank proposals by confidence
    unique_proposals = {}
    for prop in proposals:
        desc = prop["description"]
        if desc not in unique_proposals or prop["confidence"] > unique_proposals[desc]["confidence"]:
            unique_proposals[desc] = prop
    return list(unique_proposals.values()) if unique_proposals else [
        {"description": "Manual investigation required", "confidence": 0.5, "details": {}}
    ]

# Main optimization proposal function
async def propose_optimization(
    identifier: str,
    causes: List[Dict[str, Any]] = None,
    predictions: Dict[str, List[float]] = None,
    kpis: Dict[str, Dict[str, float]] = None,
    config: Dict[str, Any] = None,
    agent_id: str = "optimization_agent_1",
    source_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Propose optimizations for a given identifier based on root causes, predictions, and KPIs.

    Args:
        identifier (str): Unique identifier for the data.
        causes (list, optional): List of root causes from root_cause_analysis.py.
        predictions (dict, optional): Predicted KPIs from prediction.py.
        kpis (dict, optional): Current KPIs from kpi_monitoring.py.
        config (dict, optional): Configuration for proposal generation (e.g., thresholds).
        agent_id (str): Identifier for this optimization agent.
        source_agent (str, optional): Agent that triggered this proposal.

    Returns:
        dict: Optimization proposals and metadata.
    """
    logger.info(f"Agent {agent_id}: Generating optimization proposal for {identifier}")
    config = config or {
        "thresholds": {
            "throughput_low": 10.0,
            "latency_high": 50.0,
            "throughput_decline": 0.1,  # Per-step decline rate
            "latency_increase": 0.1     # Per-step increase rate
        }
    }

    try:
        # Ensure inputs are provided in some form
        causes = causes or []
        predictions = predictions or {}
        kpis = kpis or {}

        # Generate proposals
        proposals = generate_proposal(identifier, causes, predictions, kpis, config["thresholds"])

        # Prepare result
        result = {
            "identifier": identifier,
            "proposals": proposals,
            "status": "success",
            "agent_id": agent_id,
            "source_agent": source_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "input_summary": {
                "cause_count": len(causes),
                "prediction_columns": list(predictions.keys()),
                "kpi_columns": list(kpis.keys())
            }
        }

        # Emit event to notify other agents
        await AgentEventEmitter.emit("optimization_proposed", result, target=source_agent)

        # Notify downstream agents if actionable proposals are made
        if any(prop["description"] != "Manual investigation required" for prop in proposals):
            await AgentEventEmitter.emit(
                "optimization_actionable",
                {
                    "identifier": identifier,
                    "proposals": proposals,
                    "agent_id": agent_id
                },
                target="decision_making_agent"
            )

        logger.info(f"Agent {agent_id}: Optimization proposal completed for {identifier} with {len(proposals)} proposals")
        return result

    except Exception as e:
        logger.error(f"Agent {agent_id}: Error generating optimization proposal for {identifier}: {e}")
        error_result = {
            "identifier": identifier,
            "proposals": [{"description": "Proposal generation failed", "confidence": 0.0, "details": {"error": str(e)}}],
            "status": "error",
            "message": str(e),
            "agent_id": agent_id,
            "source_agent": source_agent
        }
        await AgentEventEmitter.emit("optimization_error", error_result, target=source_agent)
        return error_result

# Listener for multi-agent integration
async def listen_for_inputs(agent_id: str):
    """Listen for relevant events from upstream agents."""
    while True:
        # Simulate receiving an event (e.g., from root_cause_analysis.py, prediction.py, or kpi_monitoring.py)
        event = {
            "event_type": "root_cause_identified",
            "data": {
                "identifier": "test_data",
                "causes": [{"description": "Possible interference", "confidence": 0.9, "details": {}}],
                "predictions": {"throughput": [8, 7, 6], "latency": [55, 60, 65]},
                "kpis": {"throughput": {"mean": 9.0, "std": 2.0}, "latency": {"mean": 55.0, "std": 5.0}}
            }
        }
        if event["event_type"] in ["root_cause_identified", "predictions_available", "kpi_alert"]:
            logger.info(f"Agent {agent_id}: Received {event['event_type']} event")
            data = event["data"]
            result = await propose_optimization(
                identifier=data["identifier"],
                causes=data.get("causes", []),
                predictions=data.get("predictions", {}),
                kpis=data.get("kpis", {}),
                agent_id=agent_id,
                source_agent=event.get("source_agent")
            )
            logger.info(f"Agent {agent_id}: Processed event result: {result['status']}")
        await asyncio.sleep(1)  # Polling interval

if __name__ == "__main__":
    async def test_optimization_proposal():
        # Test with mock data
        causes = [{"description": "Possible interference", "confidence": 0.9, "details": {}}]
        predictions = {"throughput": [8, 7, 6], "latency": [55, 60, 65]}
        kpis = {"throughput": {"mean": 9.0, "std": 2.0}, "latency": {"mean": 55.0, "std": 5.0}}
        result = await propose_optimization("test_data", causes, predictions, kpis)
        print(result)

    asyncio.run(test_optimization_proposal())