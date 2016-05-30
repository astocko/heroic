import contextlib

import unittest

import tests.helpers as h


class TestCluster(unittest.TestCase):
    def test_grouping_aggregation(self):
        features = ['com.spotify.heroic.distributed_aggregations']

        q = "sum(10ms) by [foo] from points(0, 10000) where $key = test"

        with self.three_node_cluster(2, q, features=features) as result:
            self.assertEquals(1, len(result['result']))

            self.assertEquals(
                [[0, 4], [10, 4], [20, 2]],
                result['result'][0]['values'])

    def test_filtering_top(self):
        features = ['com.spotify.heroic.distributed_aggregations']

        q = "sum(10ms) by * | bottomk(2) | topk(1) from points(0, 10000) where $key = test"

        with self.three_node_cluster(2, q, features=features) as result:
            self.assertEquals(1, len(result['result']))

            self.assertEquals(
                [[0, 3], [10, 4]],
                result['result'][0]['values'])

    def test_filtering_bottom(self):
        features = ['com.spotify.heroic.distributed_aggregations']

        q = "sum(10ms) by * | topk(2) | bottomk(1) from points(0, 10000) where $key = test"

        with self.three_node_cluster(2, q, features=features) as result:
            self.assertEquals(1, len(result['result']))

            self.assertEquals(
                [[0, 1], [20, 2]],
                result['result'][0]['values'])

    # @h.timeout(60)
    def test_distributed_aggregation(self):
        features = ['com.spotify.heroic.distributed_aggregations']

        q = "sum(10ms) from points(0, 10000) where $key = test"

        with self.three_node_cluster(2, q, features=features) as result:
            self.assertEquals(1, len(result['result']))

            self.assertEquals(
                [[0, 4], [10, 4], [20, 2]],
                result['result'][0]['values'])

    def test_sharded_query(self):
        q = "sum(10ms) from points(0, 10000) where $key = test"

        with self.three_node_cluster(2, q) as result:
            self.assertEquals(2, len(result['result']))

            self.assertEquals(
                [[[0, 1], [20, 2]], [[0, 3], [10, 4]]],
                [r['values'] for r in result['result']])

    @contextlib.contextmanager
    def three_node_cluster(self, groups, query, features=[]):
        with h.managed_cluster(3, features=features) as nodes:
            a = nodes[0]
            b = nodes[1]

            # write some data into each shard
            a.write({"key": "test", "tags": {"foo": "bar", "bar": "a"}},
                    {"type": "points",
                     "data": [[0, 1], [20, 2]]})

            b.write({"key": "test", "tags": {"foo": "bar", "bar": "b"}},
                    {"type": "points",
                     "data": [[0, 3], [10, 4]]})

            # query for the data (without aggregation)
            result = a.query_metrics(
                {"query": query})

            self.assertEquals(200, result.status_code)

            result = result.json()

            self.assertEquals(0, len(result['errors']))

            result['result'] = sorted(result['result'],
                                      key=lambda r: r['shard'])

            yield result
