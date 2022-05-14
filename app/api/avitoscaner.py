
import threading
from concurrent import futures
from collections import defaultdict, namedtuple
# from urllib.request import urlopen, URLError
from avitoutils import getAvitoTirePricesByLocale, getAvitoTirePrices


State = namedtuple('State', 'addr ok fail')

class AvitoScaner:
    def __init__(self, pool):
        self._pool = pool
        self._lock = threading.RLock()
        self._results = defaultdict(lambda: {'ok': 0, 'fail': 0})
        self._pendings = set() #Ожидания

    def result(self, addr=None):
        def _make_state(addr, res):
            return State(addr=addr, ok=res['ok'], fail=res['fail'])
        with self._lock:
            if addr is not None:
                return _make_state(addr, self._results[addr])
            else:
                return {_make_state(addr, val)
                        for addr, val in self._results.items()}

    @property
    def pendings(self):
        with self._lock:
            return set(self._pendings)

    def scan(self, app, diametr, width, height, lon, lat, region, season, nPages, distance):
        with self._lock:
            future = self._pool.submit(self._scan, app, diametr, width, height, lon, lat, region, season, nPages, distance) #Ставим в очередь
            self._pendings.add(future)
            future.add_done_callback(self._discard_pending)
            return future

    def _discard_pending(self, future):
        with self._lock:
            self._pendings.discard(future)

    def _scan(self, app, diametr, width, height, lon, lat, region, season, nPages, distance):
        addr=f'{width}/{height}R{diametr}lon{lon}lat{lat}distance{distance}' #Формируем адрес искуственно из параметров
        try:
            ret = getAvitoTirePricesByLocale(app, diametr, width, height, lon, lat, region, season, nPages, distance)
        except:
            result = False
        else:
            result = True

        with self._lock:
            if result:
                self._results[addr]['ok'] += 1
            else:
                self._results[addr]['fail'] += 1

        return result