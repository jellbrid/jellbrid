import typing as t

from jellbrid.clients.realdebrid.types import RDBundleFileFilter


class RDBundleManager:
    def __init__(
        self,
        data: list[dict[str, dict]] | dict,
        *,
        file_filters: list[RDBundleFileFilter] | None = None,
    ):
        if isinstance(data, list):
            self.bundles = [RDBundle(d, file_filters=file_filters) for d in data]
        else:
            self.bundles = [TorrentBundle(data, file_filters=file_filters)]

    def get_bundle_of_size(self, size: int):
        for bundle in self.bundles:
            if bundle.size == size and bundle.instant_availability:
                return bundle
        return None

    def get_bundle_gte_size(self, size: int):
        for bundle in self.bundles:
            if bundle.size >= size and bundle.instant_availability:
                return bundle
        return None

    def get_bundle_with_match(self):
        for bundle in self.bundles:
            if len(bundle.matches) > 0:
                return bundle


class RDBundle:
    def __init__(
        self, bundle: dict, *, file_filters: list[t.Callable[[str], bool]] | None = None
    ):
        self.bundle = bundle
        file_filters = file_filters or []
        self.file_filters = file_filters

    @property
    def size(self):
        return len(self.bundle)

    @property
    def matches(self):
        return self._get_property_for_matches("file_id")

    @property
    def instant_availability(self):
        return self.size == len(self.matches)

    @property
    def file_ids(self):
        return self._get_property_for_matches("file_id")

    @property
    def filenames(self):
        return self._get_property_for_matches("filename")

    def _get_property_for_matches(
        self, property: t.Literal["filename"] | t.Literal["file_id"]
    ) -> list[str]:
        files = []
        for file_id, file_data in self.bundle.items():
            filename: str = file_data.get("filename", "").lower()

            for filter in self.file_filters:
                if not filter(filename):
                    break
            else:
                if property == "filename":
                    files.append(filename)
                if property == "file_id":
                    files.append(file_id)

        return files


class TorrentBundle:
    def __init__(
        self,
        pre_bundle: dict,
        *,
        file_filters: list[t.Callable[[str], bool]] | None = None,
    ):
        self.bundle = pre_bundle
        file_filters = file_filters or []
        self.file_filters = file_filters

    @property
    def size(self):
        return len(self.bundle)

    @property
    def matches(self):
        return self._get_property_for_matches("file_id")

    @property
    def instant_availability(self):
        # fake this for bundles with the correct file(s) to match
        return True

    @property
    def file_ids(self):
        return self._get_property_for_matches("file_id")

    @property
    def filenames(self):
        return self._get_property_for_matches("filename")

    def _get_property_for_matches(
        self, property: t.Literal["filename"] | t.Literal["file_id"]
    ) -> list[str]:
        files = []

        for filedata in self.bundle["files"]:
            filename: str = filedata.get("path")
            file_id: str = filedata.get("id")
            for filter in self.file_filters:
                if not filter(filename):
                    break
            else:
                if property == "filename":
                    files.append(filename)
                if property == "file_id":
                    files.append(file_id)

        return files
