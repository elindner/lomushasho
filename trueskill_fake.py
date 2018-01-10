MU = 25
SIGMA = MU / 3

class Rating(object):
  def __init__(self, mu=MU, sigma=SIGMA):
    self.mu = mu
    self.sigma = sigma

  def equals(r1, r2):
    return r1.mu == r2.mu and r1.sigma == r2.sigma
