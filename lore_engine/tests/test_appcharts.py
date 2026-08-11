import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.appcharts import run

def run_tests():
    pass



if __name__ == "__main__":
    run_tests()
