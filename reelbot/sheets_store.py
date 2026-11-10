"""Queue storage in YOUR private Google Sheet (tabs: Queue, Failed)."""
from datetime import datetime, timezone


class SheetStore:
    QUEUE = "Queue"
    FAILED = "Failed"

    def __init__(self, sheets_service, spreadsheet_id):
        self.s = sheets_service.spreadsheets()
        self.id = spreadsheet_id
        self._tab_ids = None

    # ---- helpers -------------------------------------------------------
    def _tab_id(self, title):
        if self._tab_ids is None:
            meta = self.s.get(
                spreadsheetId=self.id, fields="sheets.properties(sheetId,title)"
            ).execute()
            self._tab_ids = {
                sh["properties"]["title"]: sh["properties"]["sheetId"]
                for sh in meta["sheets"]
            }
        if title not in self._tab_ids:
            raise RuntimeError(
                f"Tab '{title}' not found. Open your add-link page once; it creates the tabs."
            )
        return self._tab_ids[title]

    def _col_a(self, title):
        res = self.s.values().get(spreadsheetId=self.id, range=f"{title}!A:A").execute()
        return [(r[0].strip() if r else "") for r in res.get("values", [])]

    def _delete_link(self, title, link):
        for i, value in enumerate(self._col_a(title)):
            if i > 0 and value == link:  # row 0 is the header
                self.s.batchUpdate(
                    spreadsheetId=self.id,
                    body={"requests": [{"deleteDimension": {"range": {
                        "sheetId": self._tab_id(title),
                        "dimension": "ROWS",
                        "startIndex": i,
                        "endIndex": i + 1,
                    }}}]},
                ).execute()
                return True
        return False

    # ---- Queue ---------------------------------------------------------
    def queue_head(self):
        for value in self._col_a(self.QUEUE)[1:]:
            if value:
                return value
        return None

    def queue_remove(self, link):
        self._delete_link(self.QUEUE, link)

    # ---- Failed --------------------------------------------------------
    def failed_list(self):
        return [v for v in self._col_a(self.FAILED)[1:] if v]

    def failed_remove(self, link):
        self._delete_link(self.FAILED, link)

    def failed_record(self, link, error):
        """Put link at the END of Failed, increasing its attempt counter."""
        attempts = 0
        res = self.s.values().get(
            spreadsheetId=self.id, range=f"{self.FAILED}!A:B"
        ).execute()
        for i, row in enumerate(res.get("values", [])):
            if i > 0 and row and row[0].strip() == link:
                try:
                    attempts = int(row[1]) if len(row) > 1 else 0
                except ValueError:
                    attempts = 0
                break
        self._delete_link(self.FAILED, link)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.s.values().append(
            spreadsheetId=self.id,
            range=f"{self.FAILED}!A:D",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [[link, attempts + 1, error, now]]},
        ).execute()
