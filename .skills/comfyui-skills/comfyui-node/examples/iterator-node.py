import random


class SamplerIterator:
    """Cycles through a list of sampler names. Auto-stops when all are exhausted."""

    _counter: dict[str, int] = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "samplers": ("STRING", {
                    "multiline": True,
                    "default": "euler\neuler_ancestral\ndpmpp_2m\ndpmpp_sde",
                }),
                "max_iterations": ("INT", {"default": 0, "min": 0, "max": 10000}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("sampler_name", "iteration")
    FUNCTION = "iterate"
    CATEGORY = "sampling"

    @classmethod
    def IS_CHANGED(cls, samplers, max_iterations, unique_id=""):
        return random.random()

    def iterate(self, samplers, max_iterations, unique_id=""):
        sampler_list = [s.strip() for s in samplers.strip().splitlines() if s.strip()]
        if not sampler_list:
            sampler_list = ["euler"]

        if unique_id not in SamplerIterator._counter:
            SamplerIterator._counter[unique_id] = 0

        idx = SamplerIterator._counter[unique_id]
        limit = max_iterations if max_iterations > 0 else len(sampler_list)

        if idx >= limit or idx >= len(sampler_list):
            SamplerIterator._counter[unique_id] = 0
            idx = 0

        sampler_name = sampler_list[idx]
        SamplerIterator._counter[unique_id] = idx + 1

        return (sampler_name, idx)


NODE_CLASS_MAPPINGS = {
    "SamplerIterator": SamplerIterator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SamplerIterator": "Sampler Iterator",
}
