import sys
import os.path
sys.path.append(os.path.join('..', 'util'))

import set_compiler
set_compiler.install()

import pyximport
pyximport.install()

import numpy as np
import pylab

import filtering
from timer import Timer
import threading

def py_median_3x3(image, iterations=10, num_threads=1):
    tmpA = image.copy()
    tmpB = np.empty_like(tmpA)

    # thread i controls every ith line of image
    threads = [None] * num_threads

    # create event where each corresponds to whether each thread and then iteration is done
    events = [[threading.Event() for i in xrange(iterations)] for j in xrange(num_threads)]

    for t_id in xrange(num_threads):
        threads[t_id] = threading.Thread(target=filter_image, args=(num_threads, t_id, events, iterations, tmpA, tmpB))
        threads[t_id].start()

    # terminate threads
    for thread in threads:
        thread.join()

    return tmpA

def filter_image(num_threads, t_id, events, iterations, tmpA, tmpB):
    for i in xrange(iterations):
        # makes the i-1 iteration of t_id-1 and t_id+1 wait before doing iteration i
        if num_threads > 1 and i > 0:
            events[(t_id-1) % num_threads][i-1].wait()
            events[(t_id+1) % num_threads][i-1].wait()

        filtering.median_3x3(tmpA, tmpB, t_id, num_threads)

        # set flag
        events[t_id][i].set()

        # swap filtering direction
        tmpA, tmpB = tmpB, tmpA

def numpy_median(image, iterations=10):
    ''' filter using numpy '''
    for i in xrange(iterations):
        padded = np.pad(image, 1, mode='edge')
        stacked = np.dstack((padded[:-2,  :-2], padded[:-2,  1:-1], padded[:-2,  2:],
                             padded[1:-1, :-2], padded[1:-1, 1:-1], padded[1:-1, 2:],
                             padded[2:,   :-2], padded[2:,   1:-1], padded[2:,   2:]))
        image = np.median(stacked, axis=2)

    return image


if __name__ == '__main__':
    input_image = np.load('image.npz')['image'].astype(np.float32)

    pylab.gray()

    pylab.imshow(input_image)
    pylab.title('original image')

    pylab.figure()
    pylab.imshow(input_image[1200:1800, 3000:3500])
    pylab.title('before - zoom')

    # verify correctness
    from_cython = py_median_3x3(input_image, 2, 5)
    from_numpy = numpy_median(input_image, 2)
    assert np.all(from_cython == from_numpy)

    with Timer() as t:
        new_image = py_median_3x3(input_image, 10, 4)

    pylab.figure()
    pylab.imshow(new_image[1200:1800, 3000:3500])
    pylab.title('after - zoom')

    print("{} seconds for 10 filter passes.".format(t.interval))
    pylab.show()
