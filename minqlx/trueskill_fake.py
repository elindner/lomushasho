import copy

MU = 25


class Rating(object):

  def __init__(self, mu=MU, sigma=0):
    self.mu = mu
    self.sigma = 0  # unused in tests
    self.exposure = mu * 2

  def __repr__(self):
    return '<Rating:%d>' % self.mu

  def __eq__(self, other):
    return self.mu == other.mu


def rate(original_ratings, ranks):
  # Fake rating will just increase mu by 1 if win, decrease if loss.
  new_ratings = copy.deepcopy(original_ratings)

  for rating in new_ratings[0]:
    rating.mu += 1 if ranks[1] == 1 else -1

  for rating in new_ratings[1]:
    rating.mu += 1 if ranks[0] == 1 else -1

  return new_ratings


def quality(ratings):
  return sum([r.mu for r in ratings[0]]) / sum([r.mu for r in ratings[1]])
