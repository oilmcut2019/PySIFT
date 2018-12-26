import numpy as np
import numpy.linalg as LA

from gaussian_filter import gaussian_filter
from orientation import quantize_orientation, cart_to_polar_grad

def get_patch_grads(p):
    r1 = np.zeros_like(p)
    r1[-1] = p[-1]
    r1[:-1] = p[1:]

    r2 = np.zeros_like(p)
    r2[0] = p[0]
    r2[1:] = p[:-1]

    dy = r1-r2

    r1[:,-1] = p[:,-1]
    r1[:,:-1] = p[:,1:]

    r2[:,0] = p[:,0]
    r2[:,1:] = p[:,:-1]

    dx = r1-r2

    return dx, dy

def get_histogram_for_subregion(m, theta, num_bin, reference_angle):
    hist = np.zeros(num_bin, dtype=np.float32)

    for mag, angle in zip(m, theta):
        binno = quantize_orientation(angle-reference_angle, num_bin)
        hist[binno] += mag

    hist /= max(1e-6, LA.norm(hist))
    hist[hist>0.2] = 0.2
    hist /= max(1e-6, LA.norm(hist))

    # in the SIFT paper, they perform trilinear interpolation on this histogram, but again I am forgoing that right now
    return hist

def get_local_descriptors(kps, octave, w=16, num_subregion=4, num_bin=8):
    descs = []

    for kp in kps:
        cx, cy, s = int(kp[0]), int(kp[1]), int(kp[2])
        s = np.clip(s, 0, octave.shape[2]-1)
        kernel = gaussian_filter(w/6) # gaussian_filter multiplies sigma by 3
        L = octave[...,s]

        t, l = max(0, cy-w//2), max(0, cx-w//2)
        b, r = min(L.shape[0], cy+w//2+1), min(L.shape[1], cx+w//2+1)
        patch = L[t:b, l:r]

        dx, dy = get_patch_grads(patch)

        if dx.shape[0] < w+1:
            if t == 0:
                kernel = kernel[kernel.shape[0]-dx.shape[0]:]
            else:
                kernel = kernel[:dx.shape[0]]
        if dx.shape[1] < w+1:
            if l == 0:
                kernel = kernel[kernel.shape[1]-dx.shape[1]:]
            else:
                kernel = kernel[:dx.shape[1]]

        if dy.shape[0] < w+1:
            if t == 0:
                kernel = kernel[kernel.shape[0]-dy.shape[0]:]
            else:
                kernel = kernel[:dy.shape[0]]
        if dy.shape[1] < w+1:
            if l == 0:
                kernel = kernel[kernel.shape[1]-dy.shape[1]:]
            else:
                kernel = kernel[:dy.shape[1]]

        m, theta = cart_to_polar_grad(dx, dy)
        dx, dy = dx*kernel, dy*kernel

        subregion_w = w//num_subregion
        featvec = np.zeros(num_bin * num_subregion**2, dtype=np.float32)

        for i in range(0, subregion_w):
            for j in range(0, subregion_w):
                t, l = i*subregion_w, j*subregion_w
                b, r = min(L.shape[0], (i+1)*subregion_w), min(L.shape[1], (j+1)*subregion_w)

                hist = get_histogram_for_subregion(m[t:b, l:r].ravel(), theta[t:b, l:r].ravel(), num_bin, kp[3])
                featvec[i*subregion_w*num_bin + j*num_bin:i*subregion_w*num_bin + (j+1)*num_bin] = hist.flatten()

        descs.append(featvec)

    return np.array(descs)