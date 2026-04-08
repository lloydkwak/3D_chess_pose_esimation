# AR Chess Queen Overlay

This project detects a chessboard in `chessboard.mp4`, estimates camera pose, and renders `queen.obj` on top of the board.

## Files

- `overlay_queen.py` — main script
- `queen.obj` — 3D queen model
- `chessboard.mp4` — input video
- `requirements.txt` — Python dependencies

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python overlay_queen.py
```

Output video: `output.mp4`

## Demo

| | |
|---|---|
| ![Snapshot 1](https://github.com/lloydkwak/3D_chess_pose_esimation/blob/main/image/1.png) | ![Snapshot 2](https://github.com/lloydkwak/3D_chess_pose_esimation/blob/main/image/2.png) |
| ![Snapshot 3](https://github.com/lloydkwak/3D_chess_pose_esimation/blob/main/image/3.png) | ![Snapshot 4](https://github.com/lloydkwak/3D_chess_pose_esimation/blob/main/image/4.png) |
| ![Snapshot 5](https://github.com/lloydkwak/3D_chess_pose_esimation/blob/main/image/5.png) | ![Snapshot 6](https://github.com/lloydkwak/3D_chess_pose_esimation/blob/main/image/6.png) |

## Quick Configuration

Edit these constants at the top of `overlay_queen.py`:

- `BOARD_SIZE` — chessboard inner-corner size
- `SQUARE_SIZE` — square size unit
- `QUEEN_POS_X`, `QUEEN_POS_Y`, `QUEEN_POS_Z` — queen position on the board
- `OBJ_PATH`, `VIDEO_PATH`, `OUTPUT_PATH` — file paths

## Notes

- Camera intrinsics are estimated from chessboard detections in the video.
- Shadow under the queen is removed.
