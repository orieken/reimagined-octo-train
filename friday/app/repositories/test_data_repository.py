# app/repositories/test_data_repository.py
class TestDataRepository:
    def __init__(self, pg_service, vector_service):
        self.pg_service = pg_service
        self.vector_service = vector_service

    async def store_report(self, report):
        """Store a report in both PostgreSQL and Qdrant."""
        # Start with PostgreSQL
        pg_report_id = await self.pg_service.store_report(report)

        # For each scenario, store tags in the scenario_tags table
        for scenario in report.scenarios:
            await self.pg_service.store_scenario_tags(scenario.id, scenario.tags)

        # Then store in vector database with reference to PostgreSQL ID
        vector_report = report.copy()
        vector_report.metadata["pg_id"] = pg_report_id
        vector_id = await self.vector_service.store_report(vector_report)

        # Update PostgreSQL with vector DB reference
        await self.pg_service.update_vector_reference(pg_report_id, vector_id)

        return pg_report_id