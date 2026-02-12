from src.core.orchestrator import MayaOrchestrator

if __name__ == "__main__":
    # 实例化并启动
    orchestrator = MayaOrchestrator(port=7022)
    orchestrator.run()