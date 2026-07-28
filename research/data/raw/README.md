# Raw experiment data

Store original CSV exports here. Suggested calibration columns:

```text
timestamp,run_id,device_id,sensor_id,reference_c,sensor_c,ambient_c,distance_mm,angle_deg,surface,sequence_number
```

Rules:

1. Keep the original sensor export unchanged.
2. Use a new file for corrected or cleaned data.
3. Record every exclusion and correction in the experiment log.
4. Do not commit credentials, personal information, or data from an energized
   installation without approval.
5. Simulator output belongs under `research/data/simulated/`, not here.
