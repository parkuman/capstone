from collections import deque

class SpeakerHistoryQueue:
    def __init__(self, speakers):
        self.queue = deque(maxlen=5)
        self.counts = {speaker: 0 for speaker in speakers}
    
    def enqueue(self, value):
        # if we've reached the max length, remove the last entry then make sure to decrement the count of that entry too
        if len(self.queue) == self.queue.maxlen:
            oldest_value = self.queue.popleft()
            self.counts[oldest_value] -= 1
            
        self.queue.append(value)
        if value in self.counts:
            self.counts[value] += 1
        else:
            self.counts[value] = 1
    
    def dequeue(self):
        value = self.queue.popleft()
        self.counts[value] -= 1
        
        return value
    
    def count(self, value):
        return self.counts.get(value, 0)