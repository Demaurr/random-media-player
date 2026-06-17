from collections import Counter


class AssociationStatsMixin:

    def get_total_associations(self, active_only: bool = False) -> int:
        return sum(
            1
            for data in self._associations.values()
            if not active_only or data.get("association_status") == "active"
        )

    def get_active_associations_count(self) -> int:
        return sum(
            1
            for data in self._associations.values()
            if data.get("association_status") == "active"
        )

    def get_inactive_associations_count(self) -> int:
        return sum(
            1
            for data in self._associations.values()
            if data.get("association_status") == "inactive"
        )

    def get_associations_by_type(self, active_only: bool = False) -> dict:
        counter = Counter()

        for (_, _, association_type), data in self._associations.items():
            if active_only and data.get("association_status") != "active":
                continue

            counter[association_type] += 1

        return dict(counter)

    def get_unique_source_count(self, active_only: bool = False) -> int:
        return len({
            src
            for (src, _, _), data in self._associations.items()
            if not active_only or data.get("association_status") == "active"
        })

    def get_unique_target_count(self, active_only: bool = False) -> int:
        return len({
            tgt
            for (_, tgt, _), data in self._associations.items()
            if not active_only or data.get("association_status") == "active"
        })

    def get_unique_hash_count(self, active_only: bool = False) -> int:
        hashes = set()

        for _, data in self._associations.items():
            if active_only and data.get("association_status") != "active":
                continue

            if data.get("source_hash"):
                hashes.add(data["source_hash"])

            if data.get("target_hash"):
                hashes.add(data["target_hash"])

        return len(hashes)

    def get_association_type_count(self, active_only: bool = False) -> int:
        return len(self.get_associations_by_type(active_only))