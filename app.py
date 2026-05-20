"""
标注审核工具 - Flask 后端
运行: python app.py
访问: http://localhost:5000
"""
import json
from pathlib import Path
from flask import Flask, jsonify, request, send_file, render_template

app = Flask(__name__)

DATASET_DIR = r"your_dataset_path"
SPLITS = ["train", "val"]
REVIEWED_FILE = Path(DATASET_DIR) / "reviewed.json"

LABEL_ORDER = [
    "class 0",    
    "class 1",    
    "class 2",
    ".......",
    "class n",
]


def load_reviewed():
    if REVIEWED_FILE.exists():
        try:
            return json.loads(REVIEWED_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_reviewed(data):
    REVIEWED_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_all_images():
    items = []
    reviewed = load_reviewed()
    for split in SPLITS:
        img_dir = Path(DATASET_DIR) / "images" / split
        lbl_dir = Path(DATASET_DIR) / "labels" / split
        if not img_dir.exists():
            continue
        for img_path in sorted(img_dir.glob("*")):
            if img_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                continue
            lbl_path = lbl_dir / (img_path.stem + ".txt")
            key = f"{img_path.stem}_{split}"
            is_reviewed = reviewed.get(key, {}).get("reviewed", False)
            items.append({
                "stem": img_path.stem,
                "img_path": str(img_path),
                "lbl_path": str(lbl_path),
                "split": split,
                "has_label": lbl_path.exists() and lbl_path.stat().st_size > 0,
                "is_reviewed": is_reviewed,
            })
    return items


@app.route("/")
def index():
    return render_template("index.html", label_order=json.dumps(LABEL_ORDER))


@app.route("/api/images")
def api_images():
    items = get_all_images()
    result = []
    for item in items:
        box_count = 0
        lbl_path = Path(item["lbl_path"])
        if lbl_path.exists() and lbl_path.stat().st_size > 0:
            box_count = sum(
                1 for line in lbl_path.read_text().strip().splitlines()
                if len(line.strip().split()) == 5
            )
        result.append({
            "stem": item["stem"],
            "split": item["split"],
            "has_label": item["has_label"],
            "box_count": box_count,
            "is_reviewed": item.get("is_reviewed", False),
        })
    return jsonify(result)


@app.route("/api/boxes/<split>/<stem>")
def api_boxes(split, stem):
    lbl_path = Path(DATASET_DIR) / "labels" / split / (stem + ".txt")
    boxes = []
    if lbl_path.exists() and lbl_path.stat().st_size > 0:
        for line in lbl_path.read_text().strip().splitlines():
            parts = line.strip().split()
            if len(parts) == 5:
                boxes.append({
                    "cls": int(parts[0]),
                    "cx": float(parts[1]),
                    "cy": float(parts[2]),
                    "w":  float(parts[3]),
                    "h":  float(parts[4]),
                })
    return jsonify(boxes)


@app.route("/api/image/<split>/<stem>")
def api_image(split, stem):
    for ext in [".jpg", ".jpeg", ".png"]:
        img_path = Path(DATASET_DIR) / "images" / split / (stem + ext)
        if img_path.exists():
            return send_file(str(img_path))
    return "Not found", 404


@app.route("/api/delete", methods=["POST"])
def api_delete():
    data = request.json
    stem = data["stem"]
    split = data["split"]
    deleted = []
    for ext in [".jpg", ".jpeg", ".png"]:
        img_path = Path(DATASET_DIR) / "images" / split / (stem + ext)
        if img_path.exists():
            img_path.unlink()
            deleted.append(str(img_path))
    lbl_path = Path(DATASET_DIR) / "labels" / split / (stem + ".txt")
    if lbl_path.exists():
        lbl_path.unlink()
        deleted.append(str(lbl_path))
    reviewed_data = load_reviewed()
    key = f"{stem}_{split}"
    if key in reviewed_data:
        del reviewed_data[key]
        save_reviewed(reviewed_data)
    return jsonify({"ok": True, "deleted": deleted})


@app.route("/api/save_labels", methods=["POST"])
def api_save_labels():
    data = request.json
    stem = data["stem"]
    split = data["split"]
    boxes = data["boxes"]
    lbl_dir = Path(DATASET_DIR) / "labels" / split
    lbl_dir.mkdir(parents=True, exist_ok=True)
    lbl_path = lbl_dir / (stem + ".txt")
    lines = [f"{b['cls']} {b['cx']:.6f} {b['cy']:.6f} {b['w']:.6f} {b['h']:.6f}" for b in boxes]
    lbl_path.write_text("\n".join(lines), encoding="utf-8")
    return jsonify({"ok": True, "saved": str(lbl_path), "box_count": len(lines)})


@app.route("/api/reviewed", methods=["POST"])
def api_set_reviewed():
    data = request.json
    stem = data["stem"]
    split = data["split"]
    reviewed = data.get("reviewed", True)
    reviewed_data = load_reviewed()
    key = f"{stem}_{split}"
    if reviewed:
        from datetime import datetime
        reviewed_data[key] = {
            "reviewed": True,
            "timestamp": datetime.now().isoformat()
        }
    else:
        reviewed_data.pop(key, None)
    save_reviewed(reviewed_data)
    return jsonify({"ok": True, "key": key, "reviewed": reviewed})


if __name__ == "__main__":
    print("=" * 55)
    print("标注审核工具启动")
    print(f"数据集路径: {DATASET_DIR}")
    print("请在浏览器访问: http://localhost:5000")
    print("=" * 55)
    app.run(debug=False, port=5000)
