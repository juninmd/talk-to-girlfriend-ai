from backend.services.reporting import reporting_service


async def generate_daily_report_now() -> str:
    """
    Manually triggers the generation and sending of the daily report.
    Useful for testing or if the scheduled report was missed.
    """
    await reporting_service.generate_daily_report()
    return "Daily report generation triggered. Check the logs and the target channel."
