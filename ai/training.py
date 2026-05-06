import argparse

from ultralytics import YOLO


def train(
    data_yaml: str,
    model: str,
    epochs: int,
    imgsz: int,
    batch: int,
    workers: int,
    device: str,
    project: str,
    name: str,
    resume: bool,
):
    net = YOLO(model)
    return net.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        workers=workers,
        device=device,
        project=project,
        name=name,
        cache=True,
        amp=True,
        resume=resume,
    )


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 aircraft model")
    parser.add_argument("--data-yaml", required=True, help="Path to data.yaml")
    parser.add_argument("--model", default="yolov8m.pt", help="Base or checkpoint model")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=1024)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--device", default="0", help="GPU id or 'cpu'")
    parser.add_argument("--project", default="runs/geoeye")
    parser.add_argument("--name", default="yolov8-aircraft")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    result = train(
        data_yaml=args.data_yaml,
        model=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=args.device,
        project=args.project,
        name=args.name,
        resume=args.resume,
    )
    print(result)


if __name__ == "__main__":
    main()
