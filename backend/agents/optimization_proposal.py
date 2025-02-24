from utils.logger import logger

def propose_optimization(identifier: str, cause: str) -> dict:
    logger.info(f"Generating optimization proposal for {identifier}")
    if "interference" in cause:
        proposal = "Adjust antenna tilt by 2 degrees or increase power by 3 dBm"
    elif "congestion" in cause:
        proposal = "Reallocate spectrum or offload traffic to adjacent cells"
    else:
        proposal = "Manual investigation required"
    return {"identifier": identifier, "proposal": proposal}
