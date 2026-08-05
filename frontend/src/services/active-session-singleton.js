// Singleton instance of ActiveSessionService to persist across navigation
import { ActiveSessionService } from './active-session-service';

let serviceInstance = null;

export function getActiveSessionService() {
    if (!serviceInstance) {
        console.log('ActiveSessionSingleton: Creating new service instance');
        serviceInstance = new ActiveSessionService();
    }
    return serviceInstance;
}

// Only call this when completely leaving the session area
export function resetActiveSessionService() {
    console.log('ActiveSessionSingleton: Resetting service instance');
    if (serviceInstance) {
        serviceInstance.close();
        serviceInstance = null;
    }
}