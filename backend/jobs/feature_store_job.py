import schedule
import time
import logging
from backend.database import SessionLocal
from backend.services.feature_store_service import FeatureStoreService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_feature_store_computation():
    logger.info("Starting scheduled Feature Store computation...")
    db = SessionLocal()
    try:
        FeatureStoreService.precompute_all_features(db)
        db.commit()
        logger.info("Feature Store computation completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during Feature Store computation: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    # Run once on startup
    run_feature_store_computation()

    # Schedule to run every hour
    schedule.every().hour.do(run_feature_store_computation)

    while True:
        schedule.run_pending()
        time.sleep(60)
