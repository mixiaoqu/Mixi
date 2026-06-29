import type { TaskProposal } from '../../../features/mixi/types'
import type { WorklogTaskDraft } from '../../../lib/mixi'
import GenericTaskCard from './GenericTaskCard'
import WorklogTaskCard from './worklog/WorklogTaskCard'

type TaskCardHostProps = {
  task: TaskProposal
  onOpenDataSources: () => void
}

export default function TaskCardHost({ task, onOpenDataSources }: TaskCardHostProps) {
  if (task.capability === 'worklog.generate') {
    return (
      <WorklogTaskCard
        onOpenDataSources={onOpenDataSources}
        task={task as TaskProposal<WorklogTaskDraft>}
      />
    )
  }

  return <GenericTaskCard task={task} />
}
