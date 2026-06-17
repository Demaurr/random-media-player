from collections import Counter


class CategoryStatsMixin:

    def get_total_categories(self) -> int:
        return len(self.category_to_files)

    def get_total_associations(self) -> int:
        """
        Total category-file associations.
        """
        return sum(
            len(files)
            for files in self.category_to_files.values()
        )

    def get_total_unique_files(self) -> int:
        """
        Unique files across all categories.
        """
        return len(self.file_to_categories)

    def get_categories_by_count(self) -> dict[str, int]:
        """
        Category -> file count.
        """
        return {
            category: len(files)
            for category, files in self.category_to_files.items()
        }

    def get_max_category(self) -> dict | None:
        counts = self.get_categories_by_count()

        if not counts:
            return None

        category = max(counts, key=counts.get)

        return {
            "name": category,
            "count": counts[category]
        }

    def get_min_category(self) -> dict | None:
        counts = self.get_categories_by_count()

        if not counts:
            return None

        category = min(counts, key=counts.get)

        return {
            "name": category,
            "count": counts[category]
        }

    def get_avg_files_per_category(self) -> float:
        total_categories = self.get_total_categories()

        if not total_categories:
            return 0

        return round(
            self.get_total_associations() / total_categories,
            2
        )

    def get_files_with_multiple_categories(self) -> int:
        return sum(
            1
            for categories in self.file_to_categories.values()
            if len(categories) > 1
        )

    def get_files_with_fingerprints(self) -> int:
        return sum(
            1
            for fingerprint in self.file_to_hash.values()
            if fingerprint
        )

    def get_files_without_fingerprints(self) -> int:
        return (
            self.get_total_unique_files()
            - self.get_files_with_fingerprints()
        )

    def get_top_categories(self, limit: int = 10) -> list[tuple[str, int]]:
        counts = self.get_categories_by_count()

        return sorted(
            counts.items(),
            key=lambda item: item[1],
            reverse=True
        )[:limit]

    def get_empty_categories(self) -> list[str]:
        return [
            category
            for category, files in self.category_to_files.items()
            if not files
        ]

    def get_category_stats(self) -> dict:
        """
        Aggregate all stats.
        """
        return {
            "total_categories": self.get_total_categories(),
            "total_associations": self.get_total_associations(),
            "total_unique_files": self.get_total_unique_files(),
            "categories_by_count": self.get_categories_by_count(),
            "max_category": self.get_max_category(),
            "min_category": self.get_min_category(),
            "avg_files_per_category": self.get_avg_files_per_category(),
            "files_with_multiple_categories": self.get_files_with_multiple_categories(),
            "files_with_fingerprints": self.get_files_with_fingerprints(),
            "files_without_fingerprints": self.get_files_without_fingerprints(),
            "top_categories": self.get_top_categories(),
            "empty_categories": self.get_empty_categories(),
        }