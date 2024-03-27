import datetime

from ..enumerator import Enumerator
from ..validator import ReportGenerationOutput, ReportGenerationParameters


async def research(params: ReportGenerationParameters) -> ReportGenerationOutput:

    start_time = datetime.datetime.now(datetime.timezone.utc)
    print({"type": "logs", "output": f"Start time: {str(start_time)}\n\n"})

    Executor = _get_report_executor(params.report_type)
    executor = Executor(params)

    report: ReportGenerationOutput = await executor.generate_report()

    end_time = datetime.datetime.now(datetime.timezone.utc)
    print({"type": "path", "output": report.report_path})
    print({"type": "logs", "output": f"\nEnd time: {end_time}\n"})
    print({"type": "logs", "output": f"\nTotal run time: {end_time - start_time}\n"})

    return report


def _get_report_executor(report_type: str):
    match report_type:
        case Enumerator.ReportType.DetailedReport.value:
            from .report_types import DetailedReport

            executor = DetailedReport
        case _:
            from .report_types import BasicReport

            executor = BasicReport

    return executor
