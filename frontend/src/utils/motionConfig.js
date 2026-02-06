export const transitions = {
    spring: {
        type: "spring",
        stiffness: 260,
        damping: 20
    },
    smooth: {
        type: "tween",
        ease: "anticipate",
        duration: 0.5
    },
    quick: {
        type: "tween",
        ease: "easeOut",
        duration: 0.2
    }
};

export const variants = {
    container: {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1,
                ...transitions.smooth
            }
        }
    },
    item: {
        hidden: { opacity: 0, y: 10 },
        visible: {
            opacity: 1,
            y: 0,
            transition: transitions.spring
        },
        exit: { opacity: 0, y: -10 }
    },
    fadeIn: {
        hidden: { opacity: 0 },
        visible: { opacity: 1 },
        exit: { opacity: 0 }
    },
    scaleUp: {
        hidden: { opacity: 0, scale: 0.95 },
        visible: {
            opacity: 1,
            scale: 1,
            transition: transitions.spring
        }
    },
    slideInRight: {
        hidden: { x: 20, opacity: 0 },
        visible: {
            x: 0,
            opacity: 1,
            transition: transitions.spring
        }
    }
};

export const hoverEffects = {
    scale: {
        scale: 1.02,
        transition: { duration: 0.2 }
    },
    lift: {
        y: -5,
        transition: { duration: 0.2 }
    },
    glow: {
        boxShadow: "0 0 20px rgba(99, 102, 241, 0.4)",
        transition: { duration: 0.2 }
    },
    buttonTap: {
        scale: 0.98
    }
};
