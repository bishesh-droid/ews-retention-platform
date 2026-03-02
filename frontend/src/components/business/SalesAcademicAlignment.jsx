import React from 'react';

/**
 * Sales & Academic Alignment Component
 *
 * Shows how well sales and academic teams coordinate on retention efforts.
 * Key for organizations where both teams share responsibility.
 */

const SalesAcademicAlignment = () => {
    return (
        <div className="premium-card business-context" style={{ marginBottom: 'var(--space-lg)' }}>
            <div style={{
                fontSize: 'var(--font-size-h2)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--business-primary)',
                marginBottom: 'var(--space-sm)'
            }}>
                Sales & Academic Alignment
            </div>
            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-xl)'
            }}>
                Coordination metrics between retention teams
            </div>

            <div style={{
                textAlign: 'center',
                padding: 'var(--space-2xl)',
                color: 'var(--gray-500)',
                background: 'var(--gray-50)',
                borderRadius: 'var(--radius-lg)',
            }}>
                Alignment metrics are not yet available from the backend (requires intervention/activity logs).
            </div>
        </div>
    );
};

export default SalesAcademicAlignment;
