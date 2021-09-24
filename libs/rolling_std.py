# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
from collections import deque
from math import sqrt


class RollingStandardDeviation:

    def __init__(self):
        self.K = 0
        self.n = 0
        self.ex = 0
        self.ex2 = 0

    def add_variable(self, x):
        if np.isnan(x): return
        if (self.n == 0):
            self.K = x
        self.n = self.n + 1
        self.ex += x - self.K
        self.ex2 += (x - self.K) * (x - self.K)

    def remove_variable(self, x):
        if np.isnan(x): return
        self.n = self.n - 1
        self.ex -= (x - self.K)
        self.ex2 -= (x - self.K) * (x - self.K)

    def get_meanvalue(self):
        if self.n == 0: return np.nan
        else:           return self.K + self.ex / self.n

    def get_variance(self):
        if self.n == 0: return np.nan
        else:           return (self.ex2 - (self.ex*self.ex)/self.n) / (self.n)

    def get_std(self):
        _variance = self.get_variance()
        if np.isnan(_variance) or _variance < 0:
            return np.nan
        else:
            return sqrt(_variance)


class RollingStandardDeviationDeque:

    def __init__(self, length):
        self.K = 0
        self.n = 0
        self.ex = 0
        self.ex2 = 0

        self.data_length = length
        self.data = deque([], self.data_length)

    def push(self, x):

        self.data.append(x)

        if np.isnan(x): return
        if (self.n == 0):
            self.K = x
        self.n = self.n + 1
        self.ex += x - self.K
        self.ex2 += (x - self.K) * (x - self.K)

        if self.n > self.data_length: self.pop()

    def pop(self):

        x = self.data.pop()

        if np.isnan(x): return
        self.n = self.n - 1
        self.ex -= (x - self.K)
        self.ex2 -= (x - self.K) * (x - self.K)

    def get_meanvalue(self):
        if self.n == 0: return np.nan
        else:           return self.K + self.ex / self.n

    def get_variance(self):
        if self.n == 0: return np.nan
        else:           return (self.ex2 - (self.ex*self.ex)/self.n) / (self.n)

    def get_std(self):
        _variance = self.get_variance()
        if np.isnan(_variance) or _variance < 0:
            return np.nan
        else:
            return sqrt(_variance)
