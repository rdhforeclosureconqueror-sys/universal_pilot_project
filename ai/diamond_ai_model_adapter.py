class AIModelAdapter:
    def __init__(self, provider: str, model_name: str, version: str):
        self.provider = provider
        self.model_name = model_name
        self.version = version

    def run_inference(self, prompt: str, context: dict) -> dict:
        if self.provider == "openai":
            return self._run_openai(prompt, context)
        elif self.provider == "local":
            return self._run_local_model(prompt, context)
        else:
            raise NotImplementedError("Provider not supported.")

    def _run_openai(self, prompt: str, context: dict) -> dict:
        import openai
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": context.get("system_message", "")},
                {"role": "user", "content": prompt}
            ]
        )
        return response.to_dict()

    def _run_local_model(self, prompt: str, context: dict) -> dict:
        return {
            "output": f"[LOCAL STUB] You said: {prompt}"
        }
