import React from 'react';
import './Skeleton.css';

const Skeleton = ({ type = 'text', count = 1, className = '' }) => {
  const skeletons = Array.from({ length: count }, (_, i) => {
    if (type === 'table') {
      return (
        <div key={i} className={`skeleton-table-row ${className}`}>
          <div className="skeleton-cell"></div>
          <div className="skeleton-cell"></div>
          <div className="skeleton-cell"></div>
          <div className="skeleton-cell"></div>
        </div>
      );
    }

    if (type === 'card') {
      return (
        <div key={i} className={`skeleton-card ${className}`}>
          <div className="skeleton skeleton-title"></div>
          <div className="skeleton skeleton-text"></div>
          <div className="skeleton skeleton-text short"></div>
        </div>
      );
    }

    if (type === 'chart') {
      return (
        <div key={i} className={`skeleton-chart ${className}`}>
          <div className="skeleton skeleton-circle"></div>
        </div>
      );
    }

    return <div key={i} className={`skeleton ${className}`}></div>;
  });

  return <>{skeletons}</>;
};

export default Skeleton;
