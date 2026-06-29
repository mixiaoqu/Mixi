import ReactMarkdown from 'react-markdown'

type WorklogPreviewProps = {
  markdown: string
}

export default function WorklogPreview({ markdown }: WorklogPreviewProps) {
  return (
    <article className="min-h-80 px-5 py-6 text-sm leading-7 text-slate-700 sm:px-6">
      <ReactMarkdown
        components={{
          h1: ({ children }) => <h1 className="mb-5 text-xl font-bold tracking-tight text-slate-950">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 mt-6 text-base font-bold text-slate-900">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 mt-5 text-sm font-bold text-slate-900">{children}</h3>,
          p: ({ children }) => <p className="mb-3">{children}</p>,
          blockquote: ({ children }) => (
            <blockquote className="mb-5 border-l-2 border-indigo-200 bg-indigo-50/60 px-3 py-2 text-xs text-slate-600 [&>p]:mb-0">
              {children}
            </blockquote>
          ),
          ul: ({ children }) => <ul className="mb-4 list-disc space-y-2 pl-5 marker:text-slate-400">{children}</ul>,
          ol: ({ children }) => <ol className="mb-4 list-decimal space-y-2 pl-5 marker:text-slate-500">{children}</ol>,
          li: ({ children }) => <li className="pl-1">{children}</li>,
          strong: ({ children }) => <strong className="font-bold text-slate-900">{children}</strong>,
          a: ({ children, href }) => (
            <a className="font-semibold text-indigo-700 underline decoration-indigo-200 underline-offset-2 hover:text-indigo-800" href={href} rel="noreferrer" target="_blank">
              {children}
            </a>
          ),
          code: ({ children }) => <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[0.9em] text-slate-800">{children}</code>,
          pre: ({ children }) => <pre className="mb-4 overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm leading-6 text-slate-100 [&_code]:bg-transparent [&_code]:p-0 [&_code]:text-inherit">{children}</pre>,
          hr: () => <hr className="my-6 border-slate-200" />,
        }}
      >
        {markdown}
      </ReactMarkdown>
    </article>
  )
}
