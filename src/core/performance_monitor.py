import numpy as np
from typing import Dict

class PerformanceMonitor:
    """Track system performance metrics"""
    def __init__(self):
        self.metrics = {
            'articles_processed': 0,
            'processing_times': [],
            'api_calls': 0,
            'errors': 0
        }

    def track_operation(self, operation: str, duration: float, success: bool = True):
        self.metrics['processing_times'].append(duration)
        if not success:
            self.metrics['errors'] += 1

    def get_stats(self) -> Dict:
        if not self.metrics['processing_times']:
            return self.metrics

        times = self.metrics['processing_times']
        return {
            **self.metrics,
            'avg_processing_time': np.mean(times),
            'total_time': sum(times),
            'success_rate': 1 - (self.metrics['errors'] / len(times)) if times else 1
        }
