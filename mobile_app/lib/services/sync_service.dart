import '../database_helper.dart';
import 'api_service.dart';

class SyncService {
  final ApiService _api;
  final DatabaseHelper _db;
  bool _isSyncing = false;

  SyncService(this._api) : _db = DatabaseHelper();

  Future<int> syncSummaries({String? token}) async {
    if (_isSyncing) return 0;
    _isSyncing = true;

    try {
      final lastDate = await _db.getLastSummaryDate();
      var since = lastDate?.add(const Duration(seconds: 1));
      print("Starting full sync since: $since");

      int totalSynced = 0;
      bool hasMore = true;

      while (hasMore) {
        final newSummaries = await _api.fetchSummaries(
          token: token,
          since: since,
          limit: 100, // Keep limit per request, but loop until done
        );

        if (newSummaries.isEmpty) {
          hasMore = false;
        } else {
          await _db.insertSummaries(newSummaries);
          totalSynced += newSummaries.length;
          print("Synced batch: ${newSummaries.length} summaries.");

          // If we received fewer items than limit, we reached the end.
          if (newSummaries.length < 100) {
            hasMore = false;
          } else {
            // Update 'since' to the date of the last item to get next batch
            since = newSummaries.last.createdAt.add(
              const Duration(milliseconds: 1),
            );
          }
        }
      }

      print("Full sync completed. Total new items: $totalSynced");
      return totalSynced;
    } catch (e) {
      print("Sync failed: $e");
      rethrow;
    } finally {
      _isSyncing = false;
    }
  }
}
