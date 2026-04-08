import cv2
import numpy as np
import sys
import os

BOARD_SIZE = (13, 9)      
SQUARE_SIZE = 1.0         
OBJ_PATH = "queen.obj"
VIDEO_PATH = "chessboard.mp4"
OUTPUT_PATH = "output.mp4"


QUEEN_POS_X = 6.0  
QUEEN_POS_Y = 4.0   


def load_obj(path):
    vertices = []
    faces = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == 'v' and len(parts) >= 4:
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif parts[0] == 'f':
                idx = []
                for p in parts[1:]:
                    idx.append(int(p.split('/')[0]) - 1)
                for i in range(1, len(idx) - 1):
                    faces.append([idx[0], idx[i], idx[i+1]])
    return np.array(vertices, dtype=np.float64), np.array(faces, dtype=np.int32)


def normalize_model(vertices, target_height=3.0):
    v = vertices.copy()
    vmin = v.min(axis=0)
    vmax = v.max(axis=0)
    center = (vmin + vmax) / 2.0

    v[:, 0] -= center[0]
    v[:, 1] -= center[1]
    v[:, 2] -= vmin[2]

    h = vmax[2] - vmin[2]
    if h > 0:
        scale = target_height / h
        v *= scale

    return v


def compute_face_normals(vertices, faces):
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return normals / norms


def decimate_faces(faces, vertices, max_faces=5000):
    if len(faces) <= max_faces:
        return faces
    idx = np.linspace(0, len(faces)-1, max_faces, dtype=int)
    return faces[idx]


def render_model(frame, vertices_2d, depths, faces, normals_cam):
    h, w = frame.shape[:2]

    face_depths = depths[faces].mean(axis=1)
    visible_mask = normals_cam[:, 2] < 0
    visible_idx = np.where(visible_mask)[0]
    sorted_idx = visible_idx[np.argsort(-face_depths[visible_idx])]

    base_color = np.array([0, 180, 255], dtype=np.float64)

    for fi in sorted_idx:
        pts = vertices_2d[faces[fi]].astype(np.int32)
        if (pts[:, 0].max() < 0 or pts[:, 0].min() >= w or
            pts[:, 1].max() < 0 or pts[:, 1].min() >= h):
            continue
        shade = 0.3 + 0.7 * abs(normals_cam[fi, 2])
        color = tuple(int(c) for c in (base_color * shade))
        cv2.fillPoly(frame, [pts.reshape(-1, 1, 2)], color)

    return frame


def main():
    raw_verts, faces = load_obj(OBJ_PATH)

    faces = decimate_faces(faces, raw_verts, max_faces=5000)

    verts = normalize_model(raw_verts, target_height=8.0)

    model_3d = np.zeros_like(verts)
    model_3d[:, 0] = verts[:, 0] + QUEEN_POS_X
    model_3d[:, 1] = verts[:, 1] + QUEEN_POS_Y
    model_3d[:, 2] = -verts[:, 2]

    objp = np.zeros((BOARD_SIZE[0] * BOARD_SIZE[1], 3), dtype=np.float32)
    objp[:, :2] = np.mgrid[0:BOARD_SIZE[0], 0:BOARD_SIZE[1]].T.reshape(-1, 2) * SQUARE_SIZE

    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    obj_points = []
    img_points = []
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    for i in range(0, total, max(1, total // 20)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(
            gray, BOARD_SIZE,
            cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_FAST_CHECK
        )
        if found:
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            obj_points.append(objp)
            img_points.append(corners2)

    ret, K, dist, _, _ = cv2.calibrateCamera(obj_points, img_points, (fw, fh), None, None)

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (fw, fh))

    frame_num = 0
    prev_rvec, prev_tvec = None, None
    SKIP = 2

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(
            gray, BOARD_SIZE,
            cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_FAST_CHECK
        )

        if found:
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

            if corners2[0, 0, 0] > corners2[-1, 0, 0]:
                corners2 = corners2[::-1].copy()

            success, rvec, tvec = cv2.solvePnP(objp, corners2, K, dist)

            if success and prev_rvec is not None:
                ok2, rvec2, tvec2 = cv2.solvePnP(objp, corners2, K, dist,
                                                    rvec=prev_rvec.copy(), tvec=prev_tvec.copy(),
                                                    useExtrinsicGuess=True)
                if ok2 and abs(tvec2[2, 0]) < 200:
                    rvec, tvec = rvec2, tvec2

            if success and abs(tvec[2, 0]) < 200:
                prev_rvec, prev_tvec = rvec, tvec

                pts_2d, _ = cv2.projectPoints(model_3d, rvec, tvec, K, dist)
                pts_2d = pts_2d.reshape(-1, 2)

                R, _ = cv2.Rodrigues(rvec)

                v0 = model_3d[faces[:, 0]]
                v1 = model_3d[faces[:, 1]]
                v2 = model_3d[faces[:, 2]]
                normals = np.cross(v1 - v0, v2 - v0)
                norms = np.linalg.norm(normals, axis=1, keepdims=True)
                norms[norms == 0] = 1
                normals = normals / norms

                normals_cam = (R @ normals.T).T

                verts_cam = (R @ model_3d.T).T + tvec.T
                depths = verts_cam[:, 2]

                frame = render_model(frame, pts_2d, depths, faces, normals_cam)

                cv2.drawFrameAxes(frame, K, dist, rvec, tvec, 2.0, 2)

        out.write(frame)
        frame_num += 1
        if frame_num % 100 == 0:
            print(f"  {frame_num}/{total} frames")

    cap.release()
    out.release()
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()