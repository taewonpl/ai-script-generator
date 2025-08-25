import { useParams } from 'react-router-dom'
import { ProjectDetailShell } from './ProjectDetailShell'

const ProjectDetailPage = () => {
  const { projectId } = useParams<{ projectId: string }>()

  if (!projectId) {
    return <div>프로젝트 ID가 필요합니다.</div>
  }

  return <ProjectDetailShell projectId={projectId} />
}

export default ProjectDetailPage
