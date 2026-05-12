"""Generate an N-scene chained workflow JSON for ComfyUI-Magic.

Creates a valid ComfyUI workflow with:
  - Model loaders (UNETLoader, DualCLIPLoader, VAELoader)
  - Sampler setup (KSamplerSelect, BasicScheduler, CFGGuider)
  - FW_LTXPipeMake bundling all resources
  - N × FW_LTXScene nodes chained via last_frame → reference_image
  - FW_VideoBatcher collecting all scene outputs
  - VHS_VideoCombine for final video output

Usage:
    python scripts/generate_workflow.py                    # Default 3 scenes
    python scripts/generate_workflow.py --scenes 5         # 5 scenes
    python scripts/generate_workflow.py --scenes 7 --frames 161  # 7 scenes, ~6.7s each
    python scripts/generate_workflow.py -o my_workflow.json # Custom output path
"""

import argparse
import json
import sys
from pathlib import Path


def make_node(node_id, node_type, pos, size=None, title=None, widgets=None,
              inputs=None, outputs=None, color=None, bgcolor=None):
    """Build a ComfyUI node dict."""
    data = {
        "id": node_id,
        "type": node_type,
        "pos": list(pos),
        "size": {"0": (size or [320, 180])[0], "1": (size or [320, 180])[1]},
        "flags": {},
        "order": 0,
        "mode": 0,
        "inputs": inputs or [],
        "outputs": outputs or [],
        "properties": {"Node name for S&R": node_type},
        "widgets_values": widgets or [],
    }
    if title:
        data["title"] = title
    if color:
        data["color"] = color
    if bgcolor:
        data["bgcolor"] = bgcolor
    return data


def make_output(name, typ, links=None):
    return {"name": name, "type": typ, "links": links or [], "slot_index": 0}


def make_input(name, typ, link=None):
    return {"name": name, "type": typ, "link": link, "slot_index": 0}


def generate_workflow(num_scenes=3, frames=97, width=768, height=512):
    """Generate the full chained workflow."""
    nodes = []
    links = []
    link_id = 1
    nid = 1

    # -- Helpers --
    def add(node):
        nonlocal nid
        nodes.append(node)
        nid += 1
        return node["id"]

    def connect(src_id, src_slot, dst_id, dst_slot, dtype):
        nonlocal link_id
        links.append([link_id, src_id, src_slot, dst_id, dst_slot, dtype])
        # Update source output links
        for n in nodes:
            if n["id"] == src_id:
                while len(n["outputs"]) <= src_slot:
                    n["outputs"].append(make_output(f"out_{len(n['outputs'])}", dtype))
                if link_id not in n["outputs"][src_slot]["links"]:
                    n["outputs"][src_slot]["links"].append(link_id)
        # Update dest input link
        for n in nodes:
            if n["id"] == dst_id:
                while len(n["inputs"]) <= dst_slot:
                    n["inputs"].append(make_input(f"in_{len(n['inputs'])}", dtype))
                n["inputs"][dst_slot]["link"] = link_id
        link_id += 1

    # ================================================================ #
    #  MODEL LOADERS (left column)
    # ================================================================ #

    unet_id = add(make_node(nid, "UNETLoader", [60, 160], [315, 58],
        widgets=["ltx-2.3-22b-distilled-1.1.safetensors", "default"],
        outputs=[make_output("MODEL", "MODEL")],
        color="#223", bgcolor="#335"))

    clip_id = add(make_node(nid, "DualCLIPLoader", [60, 280], [315, 106],
        widgets=["gemma_3_12B_it_fp8/gemma_3_12B_it_fp8-text-encoder.safetensors", "ltx", "default"],
        outputs=[make_output("CLIP", "CLIP")],
        color="#223", bgcolor="#335"))

    vae_id = add(make_node(nid, "VAELoader", [60, 440], [315, 58],
        widgets=["ltx_video_2_1_vae.safetensors"],
        outputs=[make_output("VAE", "VAE")],
        color="#223", bgcolor="#335"))

    sampler_select_id = add(make_node(nid, "KSamplerSelect", [60, 560], [315, 58],
        widgets=["euler_ancestral_cfg_pp"],
        outputs=[make_output("SAMPLER", "SAMPLER")],
        color="#223", bgcolor="#335"))

    scheduler_id = add(make_node(nid, "BasicScheduler", [60, 680], [315, 106],
        widgets=["sgm_uniform", 4, 1.0],
        inputs=[make_input("model", "MODEL")],
        outputs=[make_output("SIGMAS", "SIGMAS")],
        color="#223", bgcolor="#335"))

    guider_id = add(make_node(nid, "CFGGuider", [60, 840], [315, 98],
        widgets=[1.0],
        inputs=[make_input("model", "MODEL"), make_input("positive", "CONDITIONING"),
                make_input("negative", "CONDITIONING")],
        outputs=[make_output("GUIDER", "GUIDER")],
        color="#223", bgcolor="#335"))

    # ================================================================ #
    #  FW_LTXPipeMake
    # ================================================================ #

    pipe_id = add(make_node(nid, "FW_LTXPipeMake", [480, 360], [260, 160],
        inputs=[
            make_input("model", "MODEL"),
            make_input("vae", "VAE"),
            make_input("clip", "CLIP"),
            make_input("guider", "GUIDER"),
            make_input("sampler", "SAMPLER"),
            make_input("sigmas", "SIGMAS"),
        ],
        outputs=[make_output("ltx_pipe", "LTX_PIPE")],
        color="#2a363b", bgcolor="#3d5159"))

    # Wire loaders → pipe
    connect(unet_id, 0, pipe_id, 0, "MODEL")
    connect(vae_id, 0, pipe_id, 1, "VAE")
    connect(clip_id, 0, pipe_id, 2, "CLIP")
    connect(guider_id, 0, pipe_id, 3, "GUIDER")
    connect(sampler_select_id, 0, pipe_id, 4, "SAMPLER")
    connect(scheduler_id, 0, pipe_id, 5, "SIGMAS")

    # ================================================================ #
    #  LoadImage (starter frame for Scene 1)
    # ================================================================ #

    load_image_id = add(make_node(nid, "LoadImage", [480, 80], [260, 100],
        widgets=["example.png", "image"],
        outputs=[make_output("IMAGE", "IMAGE"), make_output("MASK", "MASK")],
        color="#223", bgcolor="#335"))

    # ================================================================ #
    #  SCENE NODES (chained)
    # ================================================================ #

    scene_prompts = [
        "A cinematic wide-angle shot of a vast ocean at golden hour, warm sunlight reflecting off gentle waves, seagulls gliding across the sky, cinematic color grading",
        "A dramatic close-up of ocean waves crashing against dark volcanic rocks, water droplets catching golden light, slow motion feel, cinematic depth of field",
        "A serene night sky over the ocean, moonlight reflecting on calm dark water, bioluminescent plankton glowing along the shoreline, peaceful atmosphere",
        "An aerial drone shot tracking along the coastline at sunrise, revealing hidden coves and sea stacks, epic scale, golden light streaming through clouds",
        "A mesmerizing underwater shot of sunlight filtering through the ocean surface, schools of fish swimming in formation, blue-green color palette, ethereal glow",
        "A sweeping panorama of a tropical beach at dusk, palm trees silhouetted against a fiery orange sky, gentle waves lapping at the shore, tranquil mood",
        "An intimate close-up of tide pools filled with colorful marine life, anemones swaying in crystal clear water, macro photography feel, vibrant detail",
        "A dramatic storm approaching over the ocean, dark clouds contrasting with shafts of golden light, massive waves building, raw power of nature",
        "A magical scene of phosphorescent waves crashing on a dark beach, each wave edge glowing electric blue, long exposure dream-like quality, surreal beauty",
        "A cinematic final shot — camera slowly pulls back to reveal the full expanse of a star-filled sky above a perfectly calm ocean, mirror reflection, infinite peace",
    ]
    neg_prompt = "blurry, distorted, static, low quality, watermark, text"

    scene_ids = []
    scene_x = 860
    for i in range(num_scenes):
        scene_y = 80 + i * 380
        prompt = scene_prompts[i % len(scene_prompts)]
        seed = 42 + i * 111
        cond = 0.9 if i < num_scenes - 1 else 0.85

        scene_id = add(make_node(nid, "FW_LTXScene", [scene_x, scene_y], [400, 310],
            title=f"🎬 Scene {i + 1}",
            widgets=[prompt, neg_prompt, frames, width, height, seed, "randomize", cond],
            inputs=[
                make_input("ltx_pipe", "LTX_PIPE"),
                make_input("reference_image", "IMAGE"),
            ],
            outputs=[
                make_output("ltx_pipe", "LTX_PIPE"),
                make_output("video_frames", "IMAGE"),
                make_output("last_frame", "IMAGE"),
                make_output("latent", "LATENT"),
            ],
            color="#1b4332", bgcolor="#2d6a4f"))

        # Fix slot_index values
        for idx, out in enumerate(nodes[-1]["outputs"]):
            out["slot_index"] = idx
        for idx, inp in enumerate(nodes[-1]["inputs"]):
            inp["slot_index"] = idx

        scene_ids.append(scene_id)

    # Wire Scene 1: pipe from PipeMake, reference from LoadImage
    connect(pipe_id, 0, scene_ids[0], 0, "LTX_PIPE")
    connect(load_image_id, 0, scene_ids[0], 1, "IMAGE")

    # Wire Scenes 2..N: pipe + last_frame chain
    for i in range(1, num_scenes):
        connect(scene_ids[i - 1], 0, scene_ids[i], 0, "LTX_PIPE")   # ltx_pipe passthrough
        connect(scene_ids[i - 1], 2, scene_ids[i], 1, "IMAGE")       # last_frame → reference_image

    # ================================================================ #
    #  FW_VideoBatcher
    # ================================================================ #

    batcher_inputs = []
    for i in range(10):
        batcher_inputs.append(make_input(f"video_{i + 1}", "IMAGE"))

    batcher_id = add(make_node(nid, "FW_VideoBatcher", [1400, 500], [280, 180],
        inputs=batcher_inputs,
        outputs=[make_output("combined_video", "IMAGE"), make_output("total_frames", "INT")],
        color="#4a1942", bgcolor="#6b2c62"))

    # Fix slot_index
    for idx, out in enumerate(nodes[-1]["outputs"]):
        out["slot_index"] = idx
    for idx, inp in enumerate(nodes[-1]["inputs"]):
        inp["slot_index"] = idx

    # Wire scene video_frames → batcher
    for i, sid in enumerate(scene_ids):
        connect(sid, 1, batcher_id, i, "IMAGE")

    # ================================================================ #
    #  VHS_VideoCombine
    # ================================================================ #

    vhs_id = add(make_node(nid, "VHS_VideoCombine", [1780, 500], [315, 218],
        widgets=[24, 0, f"magic_{num_scenes}scene", "video/h264-mp4", False, True, "", "", ""],
        inputs=[
            make_input("images", "IMAGE"),
            make_input("audio", "AUDIO"),
            make_input("meta_batch", "VHS_BatchManager"),
            make_input("vae", "VAE"),
        ],
        outputs=[make_output("Filenames", "VHS_FILENAMES")],
        color="#553322", bgcolor="#664433"))

    # Fix slot_index
    for idx, inp in enumerate(nodes[-1]["inputs"]):
        inp["slot_index"] = idx

    connect(batcher_id, 0, vhs_id, 0, "IMAGE")

    # ================================================================ #
    #  Note node with instructions
    # ================================================================ #

    note_id = add(make_node(nid, "Note", [860, 80 + num_scenes * 380], [400, 130],
        widgets=[
            "HOW TO ADD MORE SCENES:\n\n"
            "1. Right-click any Scene node → Clone\n"
            "2. Wire previous scene's 'last_frame' → new scene's 'reference_image'\n"
            "3. Wire previous scene's 'ltx_pipe' → new scene's 'ltx_pipe'\n"
            "4. Wire new scene's 'video_frames' → next free slot on VideoBatcher\n"
            "5. Change the prompt and seed"
        ],
        color="#335533", bgcolor="#446644"))

    # ================================================================ #
    #  GROUPS
    # ================================================================ #

    scene_chain_height = num_scenes * 380 + 60
    groups = [
        {"id": 1, "title": "🔧 Model Loaders", "bounding": [40, 120, 720, 860],
         "color": "#88A", "font_size": 24, "flags": {}},
        {"id": 2, "title": f"🎬 Scene Chain ({num_scenes} scenes)",
         "bounding": [840, 50, 430, scene_chain_height],
         "color": "#8A8", "font_size": 24, "flags": {}},
        {"id": 3, "title": "📹 Video Output", "bounding": [1380, 470, 740, 280],
         "color": "#AA8", "font_size": 24, "flags": {}},
    ]

    # ================================================================ #
    #  Assemble workflow JSON
    # ================================================================ #

    fps = 24
    total_frames = num_scenes * frames
    duration_secs = total_frames / fps

    workflow = {
        "last_node_id": nid - 1,
        "last_link_id": link_id - 1,
        "last_group_id": len(groups),
        "nodes": nodes,
        "links": links,
        "groups": groups,
        "config": {},
        "extra": {
            "ds": {"scale": 0.7, "offset": [0, 0]},
            "info": {
                "name": f"ComfyUI-Magic {num_scenes}-Scene Chained Video",
                "author": "ComfyUI-Magic",
                "description": (
                    f"{num_scenes}-scene chained video generation. "
                    f"Each scene: {frames} frames (~{frames / fps:.1f}s). "
                    f"Total: ~{duration_secs:.0f}s at {fps}fps."
                ),
                "version": "1.0.0",
            },
        },
        "version": 0.4,
    }

    return workflow


def main():
    parser = argparse.ArgumentParser(
        description="Generate ComfyUI-Magic chained scene workflow JSON."
    )
    parser.add_argument("--scenes", "-n", type=int, default=3,
                        help="Number of scenes (default: 3)")
    parser.add_argument("--frames", "-f", type=int, default=97,
                        help="Frames per scene — must follow 8k+1 rule (default: 97)")
    parser.add_argument("--width", "-W", type=int, default=768,
                        help="Output width in pixels (default: 768)")
    parser.add_argument("--height", "-H", type=int, default=512,
                        help="Output height in pixels (default: 512)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output file path (default: example_workflows/<name>.json)")
    args = parser.parse_args()

    # Validate 8k+1 rule
    if (args.frames - 1) % 8 != 0:
        valid = [8 * k + 1 for k in range(1, 33)]
        print(f"ERROR: frames={args.frames} does not follow the 8k+1 rule.", file=sys.stderr)
        print(f"       Valid values: {valid[:12]}...", file=sys.stderr)
        sys.exit(1)

    if args.scenes < 1 or args.scenes > 10:
        print("ERROR: scenes must be between 1 and 10.", file=sys.stderr)
        sys.exit(1)

    workflow = generate_workflow(
        num_scenes=args.scenes,
        frames=args.frames,
        width=args.width,
        height=args.height,
    )

    if args.output:
        output_path = Path(args.output)
    else:
        root = Path(__file__).resolve().parents[1]
        name = f"magic_{args.scenes}scene_{args.frames}f.json"
        output_path = root / "example_workflows" / name

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(workflow, indent=2), encoding="utf-8")

    fps = 24
    total_frames = args.scenes * args.frames
    print(f"Generated workflow: {output_path}")
    print(f"  Nodes:  {len(workflow['nodes'])}")
    print(f"  Links:  {len(workflow['links'])}")
    print(f"  Scenes: {args.scenes} × {args.frames} frames (~{args.frames / fps:.1f}s each)")
    print(f"  Total:  ~{total_frames} frames (~{total_frames / fps:.0f}s at {fps}fps)")


if __name__ == "__main__":
    main()
