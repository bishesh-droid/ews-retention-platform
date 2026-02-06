import React from 'react';
import { Form, ButtonGroup, Button } from 'react-bootstrap';
import { FaCalendar } from 'react-icons/fa';

const TimeFilter = ({ selectedRange, onRangeChange, showCustom = true }) => {
    const timeRanges = [
        { value: '7d', label: 'Last 7 Days' },
        { value: '30d', label: 'Last 30 Days' },
        { value: 'semester', label: 'This Semester' },
        { value: 'last-semester', label: 'Last Semester' },
    ];

    if (showCustom) {
        timeRanges.push({ value: 'custom', label: 'Custom Range' });
    }

    return (
        <div className="d-flex align-items-center gap-2">
            <FaCalendar className="text-muted" />
            <ButtonGroup size="sm">
                {timeRanges.map((range) => (
                    <Button
                        key={range.value}
                        variant={selectedRange === range.value ? 'primary' : 'outline-secondary'}
                        onClick={() => onRangeChange(range.value)}
                        className="px-3"
                        style={{
                            backgroundColor: selectedRange === range.value ? 'var(--primary-color)' : 'transparent',
                            borderColor: selectedRange === range.value ? 'var(--primary-color)' : 'var(--border-color)',
                        }}
                    >
                        {range.label}
                    </Button>
                ))}
            </ButtonGroup>
        </div>
    );
};

export default TimeFilter;
