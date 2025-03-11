'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

// Define the base message structure
/* eslint-disable  @typescript-eslint/no-explicit-any */
export interface EventSourceMessage {
    type: string;
    content?: string;
    payload?: any;
}

// Define the possible states of the event source
export type EventSourceStatus = 'idle' | 'connecting' | 'streaming' | 'complete' | 'error';

// Props for the hook
export interface UseEventSourceProps<T extends EventSourceMessage> {
    url: string | null;
    queryParams?: Record<string, string | string[]>;
    onComplete?: () => void;
    messageTransformer?: (message: EventSourceMessage) => T;
    enabled?: boolean;
}


// Return type for the hook
export interface UseEventSourceResult<T extends EventSourceMessage> {
    messages: T[];
    status: EventSourceStatus;
    error: string | null;
    reset: () => void;
}

/**
 * Custom hook for managing EventSource connections
 */
export function useEventSource<T extends EventSourceMessage>({
    url,
    queryParams = {},
    enabled = true,
    onComplete,
    messageTransformer = (data) => data as T,
}: UseEventSourceProps<T>): UseEventSourceResult<T> {
    const [messages, setMessages] = useState<T[]>([]);
    const [status, setStatus] = useState<EventSourceStatus>('idle');
    const [error, setError] = useState<string | null>(null);
    const eventSourceRef = useRef<EventSource | null>(null);
    const queryParamsRef = useRef<Record<string, string | string[]>>(null);

    // Function to check if queryParams have changed
    const haveQueryParamsChanged = useCallback(() => {
        if (!queryParamsRef.current) {
            return true
        }
        const prevParams = queryParamsRef.current;
        const currentParams = queryParams;

        // Check if keys are the same
        const prevKeys = Object.keys(prevParams);
        const currentKeys = Object.keys(currentParams);

        if (prevKeys.length !== currentKeys.length) {
            return true;
        }

        // Check if values are the same
        for (const key of currentKeys) {
            const prevValue = prevParams[key];
            const currentValue = currentParams[key];

            if (Array.isArray(prevValue) && Array.isArray(currentValue)) {
                if (prevValue.length !== currentValue.length) {
                    return true;
                }

                for (let i = 0; i < prevValue.length; i++) {
                    if (prevValue[i] !== currentValue[i]) {
                        return true;
                    }
                }
            } else if (prevValue !== currentValue) {
                return true;
            }
        }

        return false;
    }, [queryParams]);

    const closeConnection = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
    }, []);

    const reset = useCallback(() => {
        setMessages([]);
        setStatus('idle');
        setError(null);
        closeConnection();
        if (queryParamsRef.current) {
            queryParamsRef.current = null;
        }
    }, [closeConnection]);

    // Call onComplete when status changes to complete
    useEffect(() => {
        if (status === 'complete' && onComplete) {
            onComplete();
        }
    }, [status, onComplete]);

    // Clean up on unmount
    useEffect(() => {
        return () => {
            reset();
        };
    }, [reset]);

    useEffect(() => {
        if (!enabled || !haveQueryParamsChanged()) {
            return;
        }
        queryParamsRef.current = queryParams;

        setMessages([]);
        setError(null);
        setStatus('connecting');

        try {
            // Build URL with query parameters
            const searchParams = new URLSearchParams();
            Object.entries(queryParams).forEach(([key, value]) => {
                if (Array.isArray(value)) {
                    value.forEach(v => searchParams.append(key, v));
                } else if (value) {
                    searchParams.set(key, value);
                }
            });

            const fullUrl = `${url}${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
            closeConnection();

            const eventSource = new EventSource(fullUrl);
            eventSourceRef.current = eventSource;
            setStatus('streaming');

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'error') {
                        throw new Error(data.content || data.payload || 'An error occurred');
                    } else if (data.type == 'complete') {
                        setStatus('complete');
                        closeConnection();
                    } else {
                        const transformedMessage = messageTransformer(data);
                        setMessages((prev) => [...prev, transformedMessage]);
                    }
                } catch (error) {
                    console.error('Error parsing stream data:', error);
                    setError('Failed to process stream data. Please try again.');
                    setMessages((prev) => [
                        ...prev,
                        messageTransformer({
                            type: 'error',
                            content: 'Failed to process stream data. Please try again.'
                        })
                    ]);
                    setStatus('error');
                }
            };

            eventSource.onerror = () => {
                // FIXME: We seem to hit an error at the end of every stream, so leaving this commented for now.
                // console.error('EventSource connection error:', error);
                // setError('Connection error. Please try again.');
                // But we do need to close the connection since this also indicates the end?
                setStatus('complete');
                closeConnection();
            };
        } catch (error) {
            console.error('EventSource error:', error);
            setError('Failed to establish connection. Please try again.');
            setStatus('error');
            closeConnection();
        }
    }, [url, queryParams, haveQueryParamsChanged, closeConnection, messageTransformer, enabled]);

    return {
        messages,
        status,
        error,
        reset
    };
}