# Model Management

- Upload YOLO `.pt` weights via model upload API/UI.
- Model file checksum (`sha256`) is computed and duplicate uploads are rejected.
- Activate/deactivate models explicitly; detection requires an active model.
- Keep metrics/version metadata with each model for traceability.
- Rollback is done by re-activating an earlier validated model.
