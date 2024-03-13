class WatchDict(dict):
    def add_watch(self, key, duration=0, count=0):
        if key not in self:
            self[key] = {'duration': duration, 'count': count}
        else:
            pass
        
    def increment_duration_and_count(self, key, duration_increment=0):
        if key in self:
            self[key]['duration'] += duration_increment
            self[key]['count'] += 1
        else:
            print("Key not found in dictionary.")