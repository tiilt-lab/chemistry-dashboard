import { useEffect, useState } from 'react';
import { useParams, Outlet, useNavigate } from 'react-router-dom';
import { ActiveSessionService } from '../services/active-session-service';
import { AppSpinner } from "../spinner/spinner-component"


function SessionManagerComponent() {

  const [activeSessionService, setActiveSessionService] = useState(new ActiveSessionService());
  // { status: 'loading' | 'ready' | 'error', httpStatus? }
  const [loadState, setLoadState] = useState({ status: 'loading' })
  const { sessionId } = useParams();
  const navigate = useNavigate();


  useEffect(() => {
    if (sessionId !== undefined) {
      activeSessionService.initialize(sessionId, setLoadState);
    }

    return () => {
      activeSessionService.close();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // An expired/absent login surfaces as 401 — send the user to re-authenticate
  // instead of leaving them on a dead page.
  useEffect(() => {
    if (loadState.status === 'error' && loadState.httpStatus === 401) {
      navigate('/login');
    }
  }, [loadState, navigate])


  if (loadState.status === 'loading') {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <AppSpinner/>
      </div>
    );
  }

  if (loadState.status === 'error') {
    // 401 is being redirected to /login by the effect above; render nothing
    // for that beat. Everything else gets an actionable message rather than a
    // spinner that never resolves.
    if (loadState.httpStatus === 401) {
      return null;
    }
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="font-semibold text-tiilt-ink">This session couldn’t be loaded.</p>
        <p className="max-w-md text-sm text-tiilt-muted">
          {loadState.httpStatus
            ? `The server returned ${loadState.httpStatus}.`
            : 'A network error occurred.'}{' '}
          You may not have access to it, or it may no longer exist.
        </p>
        <button
          onClick={() => navigate('/sessions')}
          className="mt-2 rounded-lg border border-tiilt-line px-4 py-2 text-sm font-semibold text-tiilt-ink hover:bg-tiilt-line/40">
          Back to sessions
        </button>
      </div>
    );
  }

  return (
    <Outlet context={[activeSessionService, setActiveSessionService]}/>
  );

}

export {SessionManagerComponent}
