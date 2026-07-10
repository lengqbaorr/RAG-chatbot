from app.services.jobs.models import JobStage

STAGE_PROGRESS = {
    JobStage.uploading: 5,
    JobStage.loading: 15,
    JobStage.chunking: 40,
    JobStage.embedding: 70,
    JobStage.vectorstore: 90,
    JobStage.finishing: 100,
}
