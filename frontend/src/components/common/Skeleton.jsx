import React from 'react';
import './Skeleton.css';

const Skeleton = ({ type = 'text', count = 1 }) => {
  const skeletons = Array.from({ length: count }, (_, i) => {
    if (type === 'table') {
      return (
        <div key={i} className="skeleton-table-row">
          <div className="skeleton-cell"></div>
          <div className="skeleton-cell"></div>
          <div className="skeleton-cell"></div>
          <div className="skeleton-cell"></div>
        </div>
      );
    }
    return <div key={i} className="skeleton"></div>;
  });

  return <>{skeletons}</>;
};

export default Skeleton;
