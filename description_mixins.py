from collections import Counter
import datetime


class DescriptionStatsMixin:

    def _get_total_records(self):
        return len(self.descriptions)

    def _get_descriptions_with_text_count(self):
        return sum(
            1
            for data in self.descriptions.values()
            if data.get("description", "").strip()
        )

    def _get_empty_descriptions_count(self):
        return self._get_total_records() - self._get_descriptions_with_text_count()

    def _get_unique_descriptions_count(self):
        return len({
            data.get("description", "").strip()
            for data in self.descriptions.values()
            if data.get("description", "").strip()
        })

    def _get_average_description_length(self):
        lengths = [
            len(data.get("description", "").strip())
            for data in self.descriptions.values()
            if data.get("description", "").strip()
        ]

        return round(sum(lengths) / len(lengths), 2) if lengths else 0

    def _get_longest_description(self):
        longest = None

        for path, data in self.descriptions.items():
            desc = data.get("description", "").strip()

            if not desc:
                continue

            if longest is None or len(desc) > longest["length"]:
                longest = {
                    "path": path,
                    "length": len(desc),
                    "description": desc
                }

        return longest or {}

    def _get_shortest_description(self):
        shortest = None

        for path, data in self.descriptions.items():
            desc = data.get("description", "").strip()

            if not desc:
                continue

            if shortest is None or len(desc) < shortest["length"]:
                shortest = {
                    "path": path,
                    "length": len(desc),
                    "description": desc
                }

        return shortest or {}

    def _get_latest_description(self):
        latest = None

        for path, data in self.descriptions.items():
            ts_str = data.get("timestamp", "")

            try:
                ts = datetime.datetime.fromisoformat(ts_str)
            except Exception:
                continue

            if latest is None or ts > latest["datetime"]:
                latest = {
                    "path": path,
                    "timestamp": ts_str,
                    "datetime": ts
                }

        if not latest:
            return {}

        latest.pop("datetime")
        return latest

    def _get_oldest_description(self):
        oldest = None

        for path, data in self.descriptions.items():
            ts_str = data.get("timestamp", "")

            try:
                ts = datetime.datetime.fromisoformat(ts_str)
            except Exception:
                continue

            if oldest is None or ts < oldest["datetime"]:
                oldest = {
                    "path": path,
                    "timestamp": ts_str,
                    "datetime": ts
                }

        if not oldest:
            return {}

        oldest.pop("datetime")
        return oldest

    def _get_descriptions_by_date(self):
        counter = Counter()

        for data in self.descriptions.values():
            ts_str = data.get("timestamp", "")

            try:
                ts = datetime.datetime.fromisoformat(ts_str)
                counter[ts.date().isoformat()] += 1
            except Exception:
                continue

        return dict(sorted(counter.items()))

    def _get_top_words(self, limit=20, min_word_length=4):
        counter = Counter()

        for data in self.descriptions.values():
            desc = data.get("description", "")

            words = [
                word.lower()
                for word in desc.split()
                if len(word) >= min_word_length
            ]

            counter.update(words)

        return counter.most_common(limit)

    def _get_files_with_related_descriptions_count(self):
        count = 0

        for path in self.descriptions:
            related = self.get_all_related_descriptions(path)

            if len(related) > 1:
                count += 1

        return count

    def get_description_stats(self):
        return {
            "total_records": self._get_total_records(),
            "descriptions_with_text": self._get_descriptions_with_text_count(),
            "empty_descriptions": self._get_empty_descriptions_count(),
            "unique_descriptions": self._get_unique_descriptions_count(),
            "average_description_length": self._get_average_description_length(),
            "longest_description": self._get_longest_description(),
            "shortest_description": self._get_shortest_description(),
            "latest_description": self._get_latest_description(),
            "oldest_description": self._get_oldest_description(),
            "descriptions_by_date": self._get_descriptions_by_date(),
            "top_words": self._get_top_words(),
            "files_with_related_descriptions": self._get_files_with_related_descriptions_count(),
        }